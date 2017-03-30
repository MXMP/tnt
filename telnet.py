#!/usr/bin/python3

from getpass import getpass
from time import sleep
import socket
import os
from telnetlib import Telnet
from multiprocessing.dummy import Pool as ThreadPool


def send_commands(host):
    """ Подключается к хосту, авторизуется, отсылает команды из файла, сохраняет конфигурацию, пишет вывод в 
    файл отчета."""
    global user, password, commands
    print('Connect to host: {}'.format(host))
    try:
        conn = Telnet(host, 23, 10)
    except (socket.timeout, OSError):
        # если при подключении возник таймаут, значит скорее всего устройство недоступно
        print('Can\'t connect to host: {}'.format(host))
        # создаем файл по шаблону "fail-<host>.txt" и пишем в него, что хост в дауне
        write_to_file(os.path.join('reports', 'fail-' + host + '.txt'), ['Error\n', 'Host is down\n'])
    else:
        # если подключение прошло успешно, то передаем логин/пароль пользователя
        conn.write(user.encode('ascii') + b'\n')
        conn.write(password.encode('ascii') + b'\n')
        # шлем команды
        for command in commands:
            print('Send "{}" to {}'.format(command, host))
            conn.write(command.encode('ascii') + b'\n')
        # сохранием конфигурацию устройства
        conn.write(b'save\n')
        # здесь выжидаем 5 секунд, т.к. сохранение конфига происходит не сразу
        sleep(5)
        # пишем в файл вывод
        conn.write(b'logout\n')
        try:
            write_to_file(os.path.join('reports', host + '.txt'), conn.read_all().decode('ascii'))
        except socket.timeout:
            write_to_file(os.path.join('reports', 'output_fail-' + host + '.txt'), ['Error\n', 'Host is down\n'])
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
    # путь до файла с логином и паролем
    auth_file = 'auth.txt'
    # если файл с данными для авторизации существует, то берем логин и пароль из него
    if os.path.isfile(auth_file):
        auth = get_from_file(auth_file)
        user = auth[0]
        password = auth[1]
    else:
        # спрашиваем у пользователя его логин
        user = input('Enter your remote account: ')
        # спрашиваем у пользователя его пароль
        password = getpass('Password: ')

    if password:
        # читаем из файлов хосты, к которым нужно коннектится, и комманды, которые нужно передавать
        commands = get_from_file('commands.txt')
        hosts = get_from_file('hosts.txt')
        # если папка с отчетами уже создана просим удалить или переименовать ее
        try:
            os.mkdir('reports')
        except FileExistsError:
            print('Folder for reports already exists. Please delete or rename it.')
        else:
            # создаем пул с 4 воркерами
            pool = ThreadPool(4)
            # мапим функцию посыла комманд с хостами
            pool.map(send_commands, hosts)
            pool.close()
            pool.join()
