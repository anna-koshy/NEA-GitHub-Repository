#Import necessary libraries
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase, digits

app = Flask(__name__)
app.config["SECRET_KEY"] = "annakoshkey"
socketio = SocketIO(app)

rooms = {}
min_players = 4
mid_players = 6
max_players = 8

#Length: integer - the length of the code to be generated
def generate_unique_code(length): 
    #Loop until unique code is generated
    while True: 
        code = ""
        for i in range(length):
            # Generates random letter/digit for each space in code
            code += random.choice(ascii_uppercase + digits)
        
        if code not in rooms: 
            #Breaks loop as unique code has been found
            break
    return code

@app.route("/", methods=["POST", "GET"])
def start():
    session.clear()
    if request.method == "POST": 
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        
        if not name:
            return render_template("start.html", error="Please enter a name.", code=code, name=name)
        
        #Error for if user enters a name that is too short
        if len(name) < 2: 
            return render_template("start.html", error="Name must be at least 2 characters.", code=code, name=name)
        
        room = code
        if create != False:
            #Generate a unique 5-letter code for the new room
            room = generate_unique_code(5)
            #Initialises room as dictionary with empty fields
            rooms[room] = {"members": 0, "messages": [], "names": [], "host": name, "roles": [], "started": False} 

        #Error for if user tries to join a room without entering a code
        elif not code:
            return render_template("start.html", error="Please enter a room code.", code=code, name=name)

        #Error for if user enters a non-existent room code
        elif code not in rooms: 
            return render_template("start.html", error=f"Access code {code} does not match any existing lobby.", code=code, name=name)
        
        #Error for if user enters a non-unique name for that room
        elif name in rooms[room]["names"]: 
            return render_template("start.html", error=f"Choose another name: {name} already exists in the lobby.", 
            code=code, name=name)
        
        #Error for if user tries to join a full lobby
        elif rooms[room]["members"] >= max_players:
            return render_template("start.html", error="This lobby is full.", code=code, name=name)
        
        #Error for if user tries to join a lobby that has already started their game
        elif rooms[room]["started"]:
            return render_template("start.html", error="This lobby has already started the game.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        
        
        # Sends user to the room page
        return redirect(url_for("room")) 
    
    #Sends user to start page
    return render_template("start.html")

@app.route("/room")
def room():
    #Retrieve room code and user name
    room = session.get("room")
    name = session.get("name")

    #Check room code and name exist
    if room is None or name is None or room not in rooms: 
        # Send user to start page as an error has occurred
        return redirect(url_for("start")) 
    
    #Stay in room as no error has occurred
    return render_template("room.html", code=room, messages=rooms[room]["messages"], 
        names=rooms[room]["names"], host = rooms[room]["host"], is_host=(name == rooms[room]["host"])) 

@socketio.on("message")
def message(data):
    room = session.get("room")
    
    #Retrieves the identifier of the room the user is in
    if room not in rooms:
        #Returns nothing as room is non-existent
        return 
    
    content = {
        #Retrieves the name of the sending user and the content sent by the user
        "name": session.get("name"), 
        "message": data["data"]
    }
    #Sends content to appropriate room
    send(content, to=room) 
    #Stores the content in the room's message history
    rooms[room]["messages"].append(content) 
    
    
@socketio.on("connect")
def connect(auth): 
    #Retrieve room code and user name
    room = session.get("room")
    name = session.get("name")
    #Return nothing as either the room or name is non-existent
    if not room or not name:
        return
    
    #Return nothing as the room is non-existent
    if room not in rooms: 
        leave_room(room)
        return
    
    #Increments the number of members in the room by 1, 
    #adds the name of the new user to the list of names in the room, 
    rooms[room]["members"] += 1 
    rooms[room]["names"].append(name) 
    
        #Join user to room corresponding to the room code
    join_room(room) 
    #Announce to the room that a new user has joined
    send({"name": name, "message": "has entered the lobby"}, to=room) 
    
    
    
    
    
@socketio.on("disconnect")
def disconnect():
    #Retrieve room code and user name
    room = session.get("room")
    name = session.get("name")
    
    #Disconnects user from room corresponding to the room code
    leave_room(room)

    if room in rooms:
        #Announces to the room that user has left
        send({"name": name, "message": "has left the lobby"}, to=room) 
        
        #Decrements the number of members in the room by 1,
        #removes the name of the user from the list of names in the room, 
        rooms[room]["members"] -= 1 
        rooms[room]["names"].remove(name)
        
        #Ony allows room to be deleted if game has not started yet
        if not rooms[room][started]:
            #Deletes the room if the user trying to leave is the host
            if name == rooms[room]["host"]:
                socketio.emit("delete_room", rooms[room],to=room)
                del rooms[room]


@socketio.on("start_game")
def start_game():
    #Retrieve room code and user name
    room = session.get("room")
    name = session.get("name")
    
    #Checks if room is valid
    #Checks if the user is the host as the host in the only user with this permission
    if room in rooms and name == rooms[room]["host"]:
        
        #Checks if min player requirement is fulfilled
        if rooms[room]["members"] >= min_players:
            
            #Assigns two traitors if lobby has sufficient players
            if rooms[room]["members"] >= mid_players:
                for i in range(rooms[room]["members"]):
                    if i < 2:
                        rooms[room]["roles"].append("Traitor")
                    else:
                        rooms[room]["roles"].append("Faithful")
            
            #Assigns one traitor if lobby has insufficient players
            else:
                for i in range(rooms[room]["members"]):
                    if i < 1:
                        rooms[room]["roles"].append("Traitor")
                    else:
                        rooms[room]["roles"].append("Faithful")
            random.shuffle(rooms[room]["roles"])
            print(rooms[room]["roles"])
            #Toggles started status of room to True to indicate that game has started
            rooms[room]["started"] = True
            
            #Redirects all users in the room to the role assignment page
            socketio.emit("roleassignment", room = rooms[room], to=room)
        
        #Displays error message to host if min player requirement is not fulfilled
        else:
            socketio.emit("insufficient_players", to=request.sid)

@app.route("/roleassignment")
def roleassignment():
    #Retrieve room code and user name
    room = session.get("room")
    name = session.get("name")
    
    if room == None or name == None or room not in rooms: 
        # Send user to start page as an error has occurred
        return redirect(url_for("start"))
    
    player_num = rooms[room]["names"].index(name)
    role = rooms[room]["roles"][player_num]
    
    #Directing user to role assignment page
    return render_template("roleassignment.html", code = room, name = name, role = role)

@app.route("/mission")
def mission():
    room = session.get("room")
    name = session.get("name")
    
    #Check room code and name exist
    if room is None or name is None or room not in rooms: 
        # Send user to start page as an error has occurred
        return redirect(url_for("start")) 
    
    return render_template("mission.html")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)