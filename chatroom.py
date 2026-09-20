#Import necessary libraries
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase, digits

app = Flask(__name__)
app.config["SECRET_KEY"] = "annakoshkey"
socketio = SocketIO(app)

rooms = {}

def generate_unique_code(length): #Function to generate a unique room code
    while True: #Loops until unique code is generated
        code = ""
        for i in range(length):
            code += random.choice(ascii_uppercase + digits) # Generates random letter/digit for each space in code
        
        if code not in rooms: 
            break #Breaks loop as unique code has been found
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name: #Error for when no name is entered
            return render_template("home.html", error="Please enter a name.", code=code, name=name)
        
        if join != False and not code: #Error for if user tries to join a room without entering a code
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(5) #Generates a unique 5-letter code for the new room
            rooms[room] = {"members": 0, "messages": [], "names": []} #Initialises room as dictionary with members, messages and names (of members)
        elif code not in rooms: #Error for if user enters a non-existent room code
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        elif name in rooms[room] ["names"]: #Error for if user enters a non-unique name for that room
            return render_template("home.html", error="Name already taken in this room.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room")) # Sends user to the room page

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room") # Retrieves room code
    if room is None or session.get("name") is None or room not in rooms: #Checks room code and name exist
        return redirect(url_for("home")) # Sends user to home page as an error has occurred
    
    return render_template("room.html", code=room, messages=rooms[room]["messages"], names=rooms[room]["names"]) #Sends user to the appropriate room page

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return #Returns nothing as room is non-existent
    
    content = {
        "name": session.get("name"), #Gets the name of the sending user
        "message": data["data"] #Retrieves the content sent by the user
    }
    send(content, to=room) #Sends content to appropriate room
    rooms[room]["messages"].append(content) #Stores the content in the room's message history
    
@socketio.on("connect")
def connect(auth): 
    room = session.get("room")
    name = session.get("name")
    if not room or not name: #Returns nothing as either the room or name is non-existent
        return
    if room not in rooms: #Returns nothing as the room is non-existent
        leave_room(room)
        return
    
    join_room(room) #Joins user to room corresponding to the room code
    send({"name": name, "message": "has entered the room"}, to=room) #Announces to the room that a new user has joined
    rooms[room]["members"] += 1 #Increments the number of members in the room by 1
    rooms[room] ["names"].append(name) #Adds the name of the new user to the list of names in the room

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1 #Decrements the number of members in the room by 1
        rooms[room]["names"].remove(name) # Removes the name of the user from the list of names in the room
        if rooms[room]["members"] <= 0:
            del rooms[room] #Deletes the room if there are no members left
    
    send({"name": name, "message": "has left the room"}, to=room) #Announces to the room that user has left

if __name__ == "__main__":
    socketio.run(app, debug=True)