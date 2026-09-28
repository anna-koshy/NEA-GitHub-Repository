#Import necessary libraries
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase, digits

app = Flask(__name__)
app.config["SECRET_KEY"] = "annakoshkey"
socketio = SocketIO(app)

rooms = {}
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
        rules = request.form.get("rules", False)
        
        if rules:
            return redirect(url_for("rules"))
        
        if not name:
            return render_template("start.html", error="Please enter a name.", code=code, name=name)
        
        #Error for if user enters a name that is too short
        if len(name) < 2: 
            return render_template("start.html", error="Name must be at least 2 characters.", code=code, name=name)
        
        #Error for if user tries to join a room without entering a code
        if join and not code:
            return render_template("start.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            #Generate a unique 5-letter code for the new room
            room = generate_unique_code(5)
            #Initialises room as dictionary with empty fields
            rooms[room] = {"members": 0, "messages": [], "names": [], "host": ""} 
            
        #Error for if user enters a non-existent room code
        elif code not in rooms: 
            return render_template("start.html", error="Access code does not match any existing lobby.", code=code, name=name)
        
        #Error for if user enters a non-unique name for that room
        elif name in rooms[room]["names"]: 
            return render_template("start.html", error="Choose another name: this player already exists in the lobby.", 
            code=code, name=name)
        
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
    
    #Stay in room
    return render_template("room.html", code=room, messages=rooms[room]["messages"], names=rooms[room]["names"]) #Sends user to the appropriate room page


@app.route("/rules")
def rules():
    return render_template("gamerules.html")

@socketio.on("message")
def message(data):
    room = session.get("room")
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
    
    #Join user to room corresponding to the room code
    join_room(room) 
    
    #Announce to the room that a new user has joined
    send({"name": name, "message": "has entered the room"}, to=room) 
    
    #Increments the number of members in the room by 1, 
    #adds the name of the new user to the list of names in the room, 
    #and sets the first user to join the room as the host
    rooms[room]["members"] += 1 
    rooms[room] ["names"].append(name) 
    rooms[room]["host"] = rooms[room]["names"][0]
@socketio.on("disconnect")
def disconnect():
    #Retrieve room code and user name
    room = session.get("room")
    name = session.get("name")
    
    #Disconnects user from room corresponding to the room code
    leave_room(room)

    if room in rooms:
        #Announces to the room that user has left
        send({"name": name, "message": "has left the room"}, to=room) 
        
        #Decrements the number of members in the room by 1,
        #removes the name of the user from the list of names in the room, 
        #and sets the first user in the list of names as the (new) host
        rooms[room]["members"] -= 1 
        rooms[room]["names"].remove(name)
        rooms[room]["host"] = rooms[room]["names"][0]
        #Deletes the room if there are no members left
        if rooms[room]["members"] <= 0:
            del rooms[room]
    


if __name__ == "__main__":
    socketio.run(app, debug=True)