import json
import os
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

app = FastAPI()

# 儲存房間資料
rooms = {}

@app.get("/")
def health_check():
    # 專門用來給 UptimeRobot 或瀏覽器確認伺服器活著，絕不會報錯
    return PlainTextResponse("Let's Chat Server is Running!")

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    current_room = None
    player_name = ""

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            action = data.get("action")

            if action == "GET_ROOMS":
                room_list = []
                for rid, rdata in rooms.items():
                    room_list.append({
                        "id": rid,
                        "name": rdata["name"],
                        "type": rdata["type"],
                        "host": rdata["host"],
                        "current_players": len(rdata["players"])
                    })
                await websocket.send_text(json.dumps({"type": "ROOM_LIST", "rooms": room_list}))

            elif action == "CREATE_ROOM":
                room_id = str(random.randint(1000, 9999))
                r_name = data.get("room_name", "聊天房")
                r_type = data.get("room_type", "公開")
                player_name = data.get("name", "玩家")

                color = [random.randint(50, 200), random.randint(100, 255), 200]

                rooms[room_id] = {
                    "name": r_name,
                    "type": r_type,
                    "host": player_name,
                    "players": {
                        websocket: {"name": player_name, "x": 0.0, "y": 0.0, "color": color}
                    }
                }
                current_room = room_id
                
                await websocket.send_text(json.dumps({"type": "JOIN_SUCCESS", "room_id": room_id}))
                await broadcast_room_state(room_id)

            elif action == "JOIN_ROOM":
                room_id = data.get("room_id")
                player_name = data.get("name", "玩家")

                if room_id in rooms:
                    color = [random.randint(50, 200), random.randint(100, 255), 200]
                    rooms[room_id]["players"][websocket] = {
                        "name": player_name, "x": 0.0, "y": 0.0, "color": color
                    }
                    current_room = room_id

                    await websocket.send_text(json.dumps({"type": "JOIN_SUCCESS", "room_id": room_id}))
                    await broadcast_room_state(room_id)
                else:
                    await websocket.send_text(json.dumps({"type": "ERROR", "msg": "房間不存在！"}))

            elif action == "MOVE":
                if current_room and current_room in rooms:
                    if websocket in rooms[current_room]["players"]:
                        rooms[current_room]["players"][websocket]["x"] = data.get("x")
                        rooms[current_room]["players"][websocket]["y"] = data.get("y")
                        await broadcast_room_state(current_room)

            elif action == "CHAT":
                if current_room and current_room in rooms:
                    msg = data.get("msg")
                    await broadcast_chat(current_room, player_name, msg)

    except WebSocketDisconnect:
        pass
    finally:
        if current_room and current_room in rooms:
            if websocket in rooms[current_room]["players"]:
                del rooms[current_room]["players"][websocket]
                if not rooms[current_room]["players"]:
                    del rooms[current_room]
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
        "players": player_list
    })
    webs = list(rdata["players"].keys())
    for ws in webs:
        try:
            await ws.send_text(payload)
        except:
            pass

async def broadcast_chat(room_id, sender, msg):
    if room_id not in rooms: return
    payload = json.dumps({"type": "CHAT", "sender": sender, "msg": msg})
    webs = list(rdata["players"].keys())
    for ws in webs:
        try:
            await ws.send_text(payload)
        except:
            pass
