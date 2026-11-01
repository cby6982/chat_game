import asyncio
import json
import websockets

# 儲存所有房間: { room_id: { "name": 房名, "map": 地圖, "mode": 模式, "type": 類型, "max_players": 上限, "players": {ws: info} } }
rooms = {}

async def handler(websocket, path):
    current_room = None
    player_info = {}

    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")

            if action == "GET_ROOMS":
                # 回傳所有房間列表給大廳瀏覽
                room_list = []
                for rid, rdata in rooms.items():
                    room_list.append({
                        "id": rid,
                        "name": rdata["name"],
                        "type": rdata["type"],
                        "map": rdata["map"],
                        "mode": rdata["mode"],
                        "duration": rdata["duration"],
                        "current_players": len(rdata["players"]),
                        "max_players": rdata["max_players"]
                    })
                await websocket.send(json.dumps({"type": "ROOM_LIST", "rooms": room_list}))

            elif action == "CREATE_ROOM":
                import random
                room_id = str(randint_code := random.randint(1000, 9999))
                r_name = data.get("room_name", "未命名房間")
                r_type = data.get("room_type", "公開")
                r_map = data.get("map", "沙盒")
                r_mode = data.get("mode", "死鬥")
                r_duration = data.get("duration", "5分鐘")
                max_p = data.get("max_players", 12)
                p_name = data.get("name", "玩家")

                color = [random.randint(50, 200), random.randint(100, 255), 200]

                rooms[room_id] = {
                    "name": r_name,
                    "type": r_type,
                    "map": r_map,
                    "mode": r_mode,
                    "duration": r_duration,
                    "max_players": max_p,
                    "players": {
                        websocket: {"name": p_name, "x": 0.0, "y": 0.0, "color": color}
                    }
                }
                current_room = room_id
                player_info = {"name": p_name}
                
                await websocket.send(json.dumps({"type": "JOIN_SUCCESS", "room_id": room_id}))
                await broadcast_room_state(room_id)

            elif action == "JOIN_ROOM":
                room_id = data.get("room_id")
                p_name = data.get("name", "玩家")

                if room_id in rooms:
                    import random
                    color = [random.randint(50, 200), random.randint(100, 255), 200]
                    rooms[room_id]["players"][websocket] = {
                        "name": p_name, "x": 0.0, "y": 0.0, "color": color
                    }
                    current_room = room_id
                    player_info = {"name": p_name}

                    await websocket.send(json.dumps({"type": "JOIN_SUCCESS", "room_id": room_id}))
                    await broadcast_room_state(room_id)
                else:
                    await websocket.send(json.dumps({"type": "ERROR", "msg": "房間不存在！"}))

            elif action == "MOVE":
                if current_room and current_room in rooms:
                    if websocket in rooms[current_room]["players"]:
                        rooms[current_room]["players"][websocket]["x"] = data.get("x")
                        rooms[current_room]["players"][websocket]["y"] = data.get("y")
                        await broadcast_room_state(current_room)

            elif action == "CHAT":
                if current_room and current_room in rooms:
                    msg = data.get("msg")
                    sender = player_info.get("name", "某人")
                    await broadcast_chat(current_room, sender, msg)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if current_room and current_room in rooms:
            if websocket in rooms[current_room]["players"]:
                del rooms[current_room]["players"][websocket]
                if not rooms[current_room]["players"]:
                    del rooms[current_room] # 沒人了就刪除房間
                else:
                    await broadcast_room_state(current_room)

async def broadcast_room_state(room_id):
    if room_id not in rooms: return
    rdata = rooms[room_id]
    player_list = []
    for ws, info in rdata["players"].items():
        player_list.append({
            "name": info["name"], "x": info["x"], "y": info["y"], "color": info["color"]
        })
    payload = json.dumps({
        "type": "STATE",
        "room_name": rdata["name"],
        "map": rdata["map"],
        "mode": rdata["mode"],
        "players": player_list
    })
    webs = list(rdata["players"].keys())
    if webs:
        await asyncio.gather(*[ws.send(payload) for ws in webs], return_exceptions=True)

async def broadcast_chat(room_id, sender, msg):
    if room_id not in rooms: return
    payload = json.dumps({"type": "CHAT", "sender": sender, "msg": msg})
    webs = list(rooms[room_id]["players"].keys())
    if webs:
        await asyncio.gather(*[ws.send(payload) for ws in webs], return_exceptions=True)

async def main():
    import os
    port = int(os.environ.get("PORT", 8765))
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"Server started on port {port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
