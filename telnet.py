import getpass
import time
import socket
import os
from telnetlib import Telnet
from multiprocessing.dummy import Pool as ThreadPool


def send_commands(host):
    global user, password, commands
    print('Connect to host: {}'.format(host))
    try:
        conn = Telnet(host, 23, 10)
    except socket.timeout:
        print('Can\'t connect to host: {}'.format(host))
        write_to_file(os.path.join('reports', 'fail-' + host + '.txt'), ['Error', 'Host is down'])
    else:
        conn.write(user.encode('ascii') + b'\n')
        conn.write(password.encode('ascii') + b'\n')
        for command in commands:
            print('Send "{}" to {}'.format(command, host))
            conn.write(command.encode('ascii') + b'\n')
        conn.write(b'save all\n')
        time.sleep(5)
        write_to_file(os.path.join('reports', host + '.txt'), conn.read_all())
        conn.close()


def get_from_file(filename):
    f = open(filename)
    results = []
    for line in f:
        results.append(line)
    f.close()
    return results


def write_to_file(filename, data):
    f = open(filename, 'w')
    for line in data:
        f.write(line + '\n')
    f.close()


if __name__ == '__main__':
    user = input('Enter your remote account: ')
    password = getpass.getpass('Password: ')
    if password:
        commands = get_from_file('commands.txt')
        hosts = get_from_file('hosts.txt')
        try:
            os.mkdir('reports')
        except FileExistsError:
            print('Folder for reports already exists. Please delete or rename it.')
        else:
            pool = ThreadPool(2)
            pool.map(send_commands, hosts)
            pool.close()
            pool.join()
