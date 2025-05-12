import sqlite3
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os.path
from pathlib import Path


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.isfile('./database.db'):
        Path('./database.db').touch()

    conn = get_database_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS devices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_name TEXT NOT NULL UNIQUE,
                        status BOOLEAN NOT NULL,
                        additional_status TEXT
                    )''')
    conn.execute('''INSERT OR IGNORE INTO devices (device_name, status) VALUES
                    ('lamp_one', 0), ('lamp_two', 0), ('lamp_three', 0), ('terminal', 0), ('fan', 0), ('tirai_left', 0), ('tirai_right', 0), ('ac', 0), ('door', 0), ('plant', 0)''')
    conn.commit()
    conn.close()

    yield


app = FastAPI(lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_database_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def changeStatusBool(num):
    if num == 0:
        return False

    if num == 1:
        return True


# Webhook
class ArduinoItem(BaseModel):
    lamp_one: str
    lamp_two: str
    lamp_three: str
    terminal: str
    fan: object
    tirai_left: str
    tirai_right: str
    ac: object


class Password(BaseModel):
    password: str


@app.post("/password")
async def send_and_check_password(password: Password):
    if password.password == "lutfi123":
        return {
            'message': 'login success'
        }

    raise HTTPException(
        status_code=401,
        detail='wrong password, please try again'
    )


@app.post("/arduino")
async def arduino_post(arduino_items: ArduinoItem):
    def strToBool(str):
        if str == "on":
            return True

        if str == "off":
            return False

    conn = get_database_connection()
    cursor = conn.cursor()

    # Lamp code
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'lamp_one'", (strToBool(arduino_items.lamp_one),))
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'lamp_two'", (strToBool(arduino_items.lamp_two),))
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'lamp_three'",
                   (strToBool(arduino_items.lamp_three),))

    # Terminal code
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'terminal'", (strToBool(arduino_items.terminal),))

    # Tirai code
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'tirai_left'",
                   (strToBool(arduino_items.tirai_left),))
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'tirai_right'",
                   (strToBool(arduino_items.tirai_right),))

    # Fan code
    json_fan = arduino_items.fan
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'fan'", (strToBool(json_fan['status']),))
    cursor.execute("UPDATE devices SET additional_status = ? WHERE device_name = 'fan'",
                   (json.dumps({"speed": json_fan['speed']}, indent=2),))

    # AC code
    json_ac = arduino_items.ac
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'ac'", (strToBool(json_ac['status']),))
    cursor.execute("UPDATE devices SET additional_status = ? WHERE device_name = 'ac'",
                   (json.dumps({"temperature": json_ac['temperature']}, indent=2),))

    conn.commit()
    conn.close()


@app.get('/arduino')
async def arduino_get():
    conn = get_database_connection()
    cursor = conn.cursor()

    lamp_status = []

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name LIKE 'lamp%'"
    )

    rows = cursor.fetchall()

    for row in rows:
        json_data = row[0]

        lamp_status.append(changeStatusBool(json_data))

    cursor.execute(
        "SELECT status FROM devices WHERE device_name = 'terminal'"
    )
    terminal_status = cursor.fetchone()

    tirai_status = []

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'tirai_left' OR device_name = 'tirai_right'"
    )
    rows = cursor.fetchall()

    for row in rows:
        json_data = row[0]

        tirai_status.append(changeStatusBool(json_data))

    conn.close()

    return {
        "message": "success in getting device",
        "lamp_one": lamp_status[0],
        "lamp_two": lamp_status[1],
        "lamp_three": lamp_status[2],
        "terminal": changeStatusBool(terminal_status['status']),
        "tirai_left": tirai_status[0],
        "tirai_right": tirai_status[1]
    }


@app.get("/lamp/{lamp_id}")
async def get_lamp_condition(lamp_id):
    conn = get_database_connection()
    cursor = conn.cursor()

    if lamp_id == "all":
        lamp_status = []
        cursor.execute(
            f"SELECT status FROM devices WHERE device_name LIKE 'lamp%'"
        )

        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            json_data = row[0]

            lamp_status.append(changeStatusBool(json_data))

        return {
            "message": "successfully getting all lamp condition",
            "lamp_one": lamp_status[0],
            "lamp_two": lamp_status[1],
            "lamp_three": lamp_status[2]
        }
    if lamp_id not in ["one", "two", "three"]:
        return {
            "message": "lamp_id must be either one, two, or three"
        }

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'lamp_{lamp_id}'"
    )

    status = cursor.fetchone()
    conn.close()

    return {
        "message": f"successfully getting lamp {lamp_id} condition",
        "condition": changeStatusBool(status['status'])
    }


@app.get("/terminal")
async def get_terminal_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM devices WHERE device_name = 'terminal'"
    )
    status = cursor.fetchone()
    conn.close()

    return {
        "message": "successfully getting terminal condition",
        "condition": changeStatusBool(status['status'])
    }


@app.get("/tirai/{tirai_loc}")
async def get_tirai_condition(tirai_loc):
    conn = get_database_connection()
    cursor = conn.cursor()

    if tirai_loc == "all":
        tirai_status = []

        cursor.execute(
            f"SELECT status FROM devices WHERE device_name = 'tirai_left' OR device_name = 'tirai_right'"
        )
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            json_data = row[0]

            tirai_status.append(changeStatusBool(json_data))

        return {
            "message": "successfully getting all tirai condition",
            "tirai_left": tirai_status[0],
            "tirai_right": tirai_status[1]
        }
    if tirai_loc in ["left", "right"]:
        cursor.execute(
            f"SELECT status FROM devices WHERE device_name = 'tirai_{tirai_loc}'"
        )
        status = cursor.fetchone()
        conn.close()

        return {
            "message": f"successfully getting tirai {tirai_loc} condition",
            "condition": changeStatusBool(status['status']),
        }

    return {
        "message": "tirai_loc must be either left or right"
    }


@app.get("/fan")
async def get_fan_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status, additional_status FROM devices WHERE device_name = 'fan'"
    )

    fan = cursor.fetchone()
    speed = json.loads(fan['additional_status']).get('speed')
    conn.close()

    if speed == "one":
        speed = 1

    if speed == "two":
        speed = 2

    if speed == "three":
        speed = 3

    return {
        "message": "successfully getting fan condition",
        "condition": changeStatusBool(fan['status']),
        "speed_mode": speed
    }


@app.get("/ac")
async def get_ac_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status, additional_status FROM devices WHERE device_name = 'ac'"
    )

    ac = cursor.fetchone()
    temperature = json.loads(ac['additional_status']).get('temperature')
    conn.close()

    return {
        "message": "successfully getting ac condition",
        "condition": changeStatusBool(ac['status']),
        "temperature": temperature
    }


@app.get("/door")
async def get_door_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM devices WHERE device_name = 'door'"
    )
    status = cursor.fetchone()
    conn.close()

    return {
        "message": "successfully getting door condition",
        "condition": changeStatusBool(status['status'])
    }


@app.get("/plant")
async def get_plant_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM devices WHERE device_name = 'plant'"
    )
    status = cursor.fetchone()
    conn.close()

    return {
        "message": "successfully getting plant condition",
        "condition": changeStatusBool(status['status'])
    }


@app.get("/saluran")
async def get_saluran_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM devices WHERE device_name = 'saluran'"
    )
    status = cursor.fetchone()
    conn.close()

    return {
        "message": "successfully getting saluran condition",
        "condition": changeStatusBool(status['status'])
    }


@app.get("/sistem_lampu")
async def get_sistem_lampu_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM devices WHERE device_name = 'sistem_lampu'"
    )
    status = cursor.fetchone()
    conn.close()

    return {
        "message": "successfully getting sistem_lampu condition",
        "condition": changeStatusBool(status['status'])
    }


@app.get("/sistem_tirai")
async def get_sistem_tirai_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM devices WHERE device_name = 'sistem_tirai'"
    )
    status = cursor.fetchone()
    conn.close()

    return {
        "message": "successfully getting sistem_tirai condition",
        "condition": changeStatusBool(status['status'])
    }


@app.get("/sistem_tanaman")
async def get_sistem_tanaman_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM devices WHERE device_name = 'sistem_tanaman'"
    )
    status = cursor.fetchone()
    conn.close()

    return {
        "message": "successfully getting sistem_tanaman condition",
        "condition": changeStatusBool(status['status'])
    }


@app.put("/lamp/{lamp_id}")
async def set_lamp_condition(lamp_id):
    conn = get_database_connection()
    cursor = conn.cursor()

    if lamp_id not in ["one", "two", "three"]:
        return {
            "message": "lamp_id must be either one, two, or three"
        }

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'lamp_{lamp_id}'"
    )

    lamp = cursor.fetchone()

    status = changeStatusBool(lamp['status'])

    cursor.execute(
        f"UPDATE devices SET status = ? WHERE device_name = 'lamp_{lamp_id}'",
        (not status,)
    )

    conn.commit()
    conn.close()
    return {
        "message": f"successfully switch for lamp {lamp_id}"
    }


@app.post("/terminal")
async def switch_terminal_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'terminal'"
    )

    terminal = cursor.fetchone()
    status = changeStatusBool(terminal['status'])

    cursor.execute(
        "UPDATE devices SET status = ? WHERE device_name = 'terminal'",
        (not status,)
    )

    conn.commit()
    conn.close()

    return {
        "message": f"successfully switch terminal"
    }


@app.put("/tirai/{tirai_direction}")
async def set_tirai_condition(tirai_direction):
    conn = get_database_connection()
    cursor = conn.cursor()
    if tirai_direction not in ["left", "right"]:
        return {
            "message": "tirai_direction must be either left or right"
        }

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'tirai_{tirai_direction}'"
    )

    tirai = cursor.fetchone()
    status = changeStatusBool(tirai['status'])

    cursor.execute(
        f"UPDATE devices SET status = ? WHERE device_name = 'tirai_{tirai_direction}'",
        (not status,)
    )

    conn.commit()
    conn.close()

    return {
        "message": f"successfully switch tirai_{tirai_direction}"
    }


@app.put("/fan/condition")
async def set_fan_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'fan'"
    )

    fan = cursor.fetchone()
    status = changeStatusBool(fan['status'])

    cursor.execute(
        "UPDATE devices SET status = ? WHERE device_name = 'fan'",
        (not status,)
    )

    conn.commit()
    conn.close()

    return {
        "message": f"successfully switch fan"
    }


# @app.put("/fan/speed/{fan_speed}")
# async def set_fan_speed(fan_speed):
#     if fan_speed not in ["1", "2", "3"]:
#         return {
#             "message": "fan_speed must be either 1, 2, or 3"
#         }
#
#     conn = get_database_connection()
#     cursor = conn.cursor()
#
#     cursor.execute(
#         f"SELECT additional_status FROM devices WHERE device_name = 'fan'"
#     )
#
#     fan = cursor.fetchone()
#     speed = changeStatusBool(tirai['status'])
#
#     cursor.execute(
#         "UPDATE devices SET additional_status = ? WHERE device_name = 'fan'",
#         (json.dumps(
#             {"speed": int(fan_speed)}
#             , indent=2),)
#     )
#
#     conn.commit()
#     conn.close()
#
#     return {
#         "message": f"successfully change fan speed to {fan_speed}"
#     }


@app.put("/ac/condition}")
async def set_ac_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'ac'"
    )

    ac = cursor.fetchone()
    status = changeStatusBool(ac['status'])

    cursor.execute(
        "UPDATE devices SET status = ? WHERE device_name = 'ac'",
        (not status,)
    )

    conn.commit()
    conn.close()

    return {
        "message": f"successfully switch ac"
    }


# @app.put("/ac/temperature/{ac_temperature}")
# async def set_ac_temperature(ac_temperature):
#     if int(ac_temperature) < 16 and int(ac_temperature) > 32:
#         return {
#             "message": "ac_temperature must be in range of 16 until 32"
#         }
#
#     conn = get_database_connection()
#     cursor = conn.cursor()
#
#     cursor.execute(
#         "UPDATE devices SET additional_status = ? WHERE device_name = 'ac'",
#         (json.dumps({
#             "temperature": int(ac_temperature)
#         }, indent=2),)
#     )
#
#     conn.commit()
#     conn.close()
#
#     return {
#         "message": f"successfully change ac temperature to {ac_temperature}"
#     }


@app.put("/door")
async def set_door_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'door'"
    )

    door = cursor.fetchone()
    status = changeStatusBool(door['status'])

    cursor.execute(
        "UPDATE devices SET status = ? WHERE device_name = 'door'",
        (not status,)
    )

    conn.commit()
    conn.close()

    return {
        "message": f"successfully switch door"
    }


@app.put("/plant")
async def set_plant_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'plant'"
    )

    plant = cursor.fetchone()
    status = changeStatusBool(plant['status'])

    cursor.execute(
        "UPDATE devices SET status = ? WHERE device_name = 'plant'",
        (not status,)
    )

    conn.commit()
    conn.close()

    return {
        "message": f"successfully switch plant"
    }


@app.put("/saluran")
async def set_saluran_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'saluran'"
    )

    saluran = cursor.fetchone()
    status = changeStatusBool(saluran['status'])

    cursor.execute(
        "UPDATE devices SET status = ? WHERE device_name = 'saluran'",
        (not status,)
    )

    conn.commit()
    conn.close()

    return {
        "message": f"successfully switch saluran"
    }


@app.put("/sistem_lampu")
async def set_sistem_lampu_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'sistem_lampu'"
    )

    sistem_lampu = cursor.fetchone()
    status = changeStatusBool(sistem_lampu['status'])

    cursor.execute(
        "UPDATE devices SET status = ? WHERE device_name = 'sistem_lampu'",
        (not status,)
    )

    conn.commit()
    conn.close()

    return {
        "message": f"successfully switch sistem_lampu"
    }


@app.put("/sistem_tanaman")
async def set_sistem_tanaman_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'sistem_tanaman'"
    )

    sistem_tanaman = cursor.fetchone()
    status = changeStatusBool(sistem_tanaman['status'])

    cursor.execute(
        "UPDATE devices SET status = ? WHERE device_name = 'sistem_tanaman'",
        (not status,)
    )

    conn.commit()
    conn.close()

    return {
        "message": f"successfully switch sistem_tanaman"
    }


@app.put("/sistem_tirai")
async def set_sistem_tirai_condition():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT status FROM devices WHERE device_name = 'sistem_tirai'"
    )

    sistem_tirai = cursor.fetchone()
    status = changeStatusBool(sistem_tirai['status'])

    cursor.execute(
        "UPDATE devices SET status = ? WHERE device_name = 'sistem_tirai'",
        (not status,)
    )

    conn.commit()
    conn.close()

    return {
        "message": f"successfully switch sistem_tirai"
    }