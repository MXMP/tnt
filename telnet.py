#!/usr/bin/python3

from time import sleep
import socket
import os
import sys
import configparser
from telnetlib import Telnet
from multiprocessing.dummy import Pool as ThreadPool


def send_commands(host):
    """ Подключается к хосту, авторизуется, отсылает команды из файла, сохраняет конфигурацию (если нужно),
    пишет вывод в файл отчета."""
    global user, password, commands, config
    reports_foldername = config.get('reports', 'foldername', fallback='reports')
    sleep_after = config.getint('commands', 'sleep_after', fallback=2)

    print('Connect to host: {}'.format(host))
    try:
        conn = Telnet(host, config.getint('telnet', 'Port', fallback=23),
                      config.getint('telnet', 'Timeout', fallback=10))
    except (socket.timeout, OSError):
        # если при подключении возник таймаут, значит скорее всего устройство недоступно
        print('Can\'t connect to host: {}'.format(host))
        # создаем файл по шаблону "fail-<host>.txt" и пишем в него, что хост в дауне
        write_to_file(os.path.join(reports_foldername, 'fail-' + host + '.txt'),
                      ['Error\n', 'Host is down\n'])
    else:
        # если подключение прошло успешно, то передаем логин/пароль пользователя
        conn.write(user.encode('ascii') + b'\n')
        conn.write(password.encode('ascii') + b'\n')

        # шлем команды
        for command in commands:
            print('Send "{}" to {}'.format(command, host))
            conn.write(command.encode('ascii') + b'\n')
            sleep(sleep_after)

        # если нужно сохранием конфигурацию устройства
        if config.getboolean('hosts', 'do_save', fallback=True):
            conn.write(b'save\n')
            # здесь выжидаем 5 секунд, т.к. сохранение конфига происходит не сразу
            sleep(5)

        # разлогиниваемся
        conn.write(b'logout\n')

        # пишем в файл вывод
        try:
            write_to_file(os.path.join(reports_foldername, host + '.txt'), conn.read_all().decode('ascii'))
        except socket.timeout:
            write_to_file(os.path.join(reports_foldername, 'output_fail-' + host + '.txt'),
                          ['Error\n', 'Host is down\n'])
        except (BrokenPipeError, ConnectionResetError):
            # такое происходит когда соединение закрылось (например если много раз неправильно введен логин/пароль)
            write_to_file(os.path.join(reports_foldername, 'output_fail-' + host + '.txt'),
                          ['Error\n', 'Connection is closed\n'])
        finally:
            conn.close()


def get_from_file(filename):
    """ Просто читает данные из файла построчно и возвращает их в виде списка."""
    results = []
    f = open(filename)
    for line in f:
        results.append(line.rstrip())
    f.close()
    return results


def write_to_file(filename, data):
    """ Просто пишет данные в файл построчно."""
    f = open(filename, 'w')
    for line in data:
        f.write(line)
    f.close()


if __name__ == '__main__':
    # читаем конфиг
    config = configparser.ConfigParser()

    # проверяем наличие файл конфига
    if not os.path.isfile('config.ini'):
        print('Couldn\'t find "config.ini" file. Using default values.')
    else:
        config.read('config.ini')

    # данные для авторизации
    user = config.get('auth', 'User', fallback='admin')
    password = config.get('auth', 'Password', fallback='admin')

    # читаем из файлов хосты, к которым нужно коннектится, и комманды, которые нужно передавать
    commands = get_from_file(config.get('commands', 'filename', fallback='commands.txt'))
    hosts = get_from_file(config.get('hosts', 'filename', fallback='hosts.txt'))

    try:
        os.mkdir(config.get('reports', 'foldername', fallback='reports'))
    except FileExistsError:
        # если папка с отчетами уже создана просим удалить или переименовать ее
        print('Folder for reports already exists. Please delete or rename it.')
        sys.exit()
    else:
        # создаем пул с воркерами
        pool = ThreadPool(config.getint('main', 'Workers', fallback=4))
        # мапим функцию посыла комманд с хостами
        pool.map(send_commands, hosts)
        pool.close()
        pool.join()
