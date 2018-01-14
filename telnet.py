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
    reports_foldername = config['reports']['foldername']

    print('Connect to host: {}'.format(host))
    try:
        conn = Telnet(host, config['telnet'].getint('Port'), config['telnet'].getint('Timeout'))
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

        # если нужно сохранием конфигурацию устройства
        if config['hosts'].getboolean('do_save'):
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
    # работаем только если есть файл конфига
    if os.path.isfile('config.ini'):
        # читаем конфиг
        config = configparser.ConfigParser()
        config.read('config.ini')

        # данные для авторизации
        user = config['auth']['User']
        password = config['auth']['Password']

        # читаем из файлов хосты, к которым нужно коннектится, и комманды, которые нужно передавать
        commands = get_from_file(config['commands']['filename'])
        hosts = get_from_file(config['hosts']['filename'])

        try:
            os.mkdir(config['reports']['foldername'])
        except FileExistsError:
            # если папка с отчетами уже создана просим удалить или переименовать ее
            print('Folder for reports already exists. Please delete or rename it.')
            sys.exit()
        else:
            # создаем пул с 4 воркерами
            pool = ThreadPool(4)
            # мапим функцию посыла комманд с хостами
            pool.map(send_commands, hosts)
            pool.close()
            pool.join()
    else:
        print('Please create "config.ini" file.')
        sys.exit()
