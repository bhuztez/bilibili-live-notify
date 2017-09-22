#!/usr/bin/env python3

import struct, json
from asyncio import (get_event_loop, sleep, ensure_future, open_connection)
import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify


HOST = 'livecmt-2.bilibili.com'
PORT = 788


def send_notify(summary, body):
    n = Notify.Notification.new(summary, body, "dialog-information")
    n.show()


def handle_msg(msg):
    cmd = msg['cmd']

    if cmd == 'WELCOME':
        data = msg['data']
        send_notify(data['uname'], "进入直播间")

    elif cmd == 'DANMU_MSG':
        info = msg['info']
        name = "[UL{}] {}".format(info[4][0], info[2][1])
        if (info[3]):
            name = "[{} {}]{}".format(info[3][1], info[3][0], name)
        send_notify(name, info[1])

    elif cmd == 'SEND_GIFT':
        data = msg['data']
        send_notify(data['uname'], "{} {} x{}".format(data['action'], data['giftName'], data['num']))

    elif cmd == 'ROOM_BLOCK_MSG':
        send_notify(msg['uname'], "已被管理员禁言")

    elif cmd == 'SYS_MSG':
        pass
    elif cmd == 'WELCOME_GUARD':
        pass
    else:
        print("MSG:", msg)


def encode(action, data):
    o = json.dumps(data, separators=(',', ':')).encode('ascii')
    return struct.pack("!LLLL", len(o) + 16, 0x100001, action, 1) + o


def send_packet(writer, action, data=''):
    writer.write(encode(action, data))


async def read_packet(reader):
    l = await reader.readexactly(4)
    p = await reader.readexactly(struct.unpack("!L", l)[0] - 4)
    action = struct.unpack("!L", p[4:8])[0]
    payload = p[12:]
    return (action, payload)


async def start_heartbeat(writer, interval=30):
    while True:
        send_packet(writer, 2)
        await sleep(interval)


async def start(roomid):
    reader, writer = await open_connection(HOST, PORT)
    send_packet(writer, 7, {"uid": 0, "roomid": roomid, "protover": 1})

    ensure_future(start_heartbeat(writer))

    while True:
        action, payload = await read_packet(reader)

        if action == 3:
            print("ONLINE:", struct.unpack("!L", payload)[0])
        elif action == 5:
            try:
                handle_msg(json.loads(payload.decode('utf-8')))
            except json.decoder.JSONDecodeError:
                print("DECODE FAILED", payload)
        elif action == 8:
            pass
        else:
            print("RECV:", action, payload)


def run_loop(loop):
    try:
        loop.run_forever()
    finally:
        loop.close()


def main(roomid):
    Notify.init("bilibili")

    ensure_future(start(roomid))

    loop = get_event_loop()
    run_loop(loop)


if __name__ == '__main__':
    import sys
    main(int(sys.argv[1]))
