import asyncio
import json
import websockets

# 儲存房間資料: { room_code: { websocket: { "name": 名字, "x": 0, "y": 0, "color": [r,g,b] } } }
rooms = {}

async def handler(websocket, path):
    room_code = None
    player_name = None
    
    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")

            if action == "JOIN":
                room_code = data.get("room")
                player_name = data.get("name")
                
                if room_code not in rooms:
                    rooms[room_code] = {}
                
                # 簡單指定隨機顏色
                import random
                color = [random.randint(50, 200), random.randint(100, 255), 200]
                
                rooms[room_code][websocket] = {
                    "name": player_name,
                    "x": 0.0,
                    "y": 0.0,
                    "color": color
                }
                
                # 廣播更新房間內所有人列表
                await broadcast_room(room_code)

            elif action == "MOVE":
                if room_code and websocket in rooms.get(room_code, {}):
                    rooms[room_code][websocket]["x"] = data.get("x")
                    rooms[room_code][websocket]["y"] = data.get("y")
                    await broadcast_room(room_code)

            elif action == "CHAT":
                if room_code:
                    msg = data.get("msg")
                    await broadcast_chat(room_code, player_name, msg)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if room_code and room_code in rooms:
            if websocket in rooms[room_code]:
                del rooms[room_code][websocket]
                if not rooms[room_code]:
                    del rooms[room_code] # 房間沒人了就刪除
                else:
                    await broadcast_room(room_code)

async def broadcast_room(room_code):
    if room_code not in rooms: return
    
    player_list = []
    for ws, info in rooms[room_code].items():
        player_list.append({
            "name": info["name"],
            "x": info["x"],
            "y": info["y"],
            "color": info["color"]
        })
    
    payload = json.dumps({"type": "STATE", "players": player_list})
    
    # 傳送給該房間所有人
    webs = list(rooms[room_code].keys())
    if webs:
        await asyncio.gather(*[ws.send(payload) for ws in webs], return_exceptions=True)

async def broadcast_chat(room_code, sender, msg):
    if room_code not in rooms: return
    payload = json.dumps({"type": "CHAT", "sender": sender, "msg": msg})
    webs = list(rooms[room_code].keys())
    if webs:
        await asyncio.gather(*[ws.send(payload) for ws in webs], return_exceptions=True)

async def main():
    # Render 會自動指定 PORT 環境變數
    import os
    port = int(os.environ.get("PORT", 8765))
    
    # 啟動 WebSocket 伺服器
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"Server started on port {port}")
        await asyncio.Future() #永遠運行

if __name__ == "__main__":
    asyncio.run(main())