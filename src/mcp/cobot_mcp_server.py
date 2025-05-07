# robot_arm_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context
import asyncio, time
from xarm import version
from xarm.wrapper import XArmAPI
from cobot_setup import RobotMain
import pymongo
import os
import numpy as np
import logging

logger = logging.getLogger(__name__)

# SETTINGS
CENTER_TOLERANCE_X = 3 # Tolerance for obj tracking (mm)
CENTER_TOLERANCE_Y = 3 # Tolerance for obj tracking (mm)
RETRY_COUNT = 20
MIN_Z = 10 # Minimum height to maintain when picking up object
STEP_SIZE_Z = 10 # Step size to move down while checking for suction (mm)
DROP_X = 148.1
DROP_Y = 181.9
DROP_Z = 80

# Create an MCP server
# mcp = FastMCP("Demo")
mcp = FastMCP("robot_arm", 
            port=8080,  # Sets the default SSE port
            description="MCP server for giving commands to the robot arm, cobot",
            transport='sse',
            host="0.0.0.0", # Sets the default SSE host
            log_level="INFO", # Sets the logging level
            on_duplicate_tools="warn" # Warn if tools with the same name are registered (options: 'error', 'warn', 'ignore')
            )

# Cobot setup
XARM_IP = os.getenv('XARMAPI_IP', '192.168.0.153')
arm = XArmAPI(XARM_IP, baud_checkset=False)
robot_main = RobotMain(arm)

# MongoDB Setup
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongo:27017/objs_db')
mongo_client = pymongo.MongoClient(MONGO_URI)
objs_db = mongo_client.get_database()
latest_obj = objs_db["latest_detected_obj"] # To get the latest obj detection results

@mcp.tool()
def robot_square_move(ctx: Context) -> str:
    """Instruct cobot arm to move in a square movement.

    This tool instructs or commands the robot arm to move in a square.

    Args:
        ctx: The MCP server provided context 
    """
    print(f"Instructing cobot to move in a square")
    time.sleep(3)
    robot_main.move_square()
    return f"Instructing cobot to move in a square"

@mcp.tool()
def robot_circle_move(ctx: Context) -> str:
    """Instruct cobot arm to move in a circle movement.

    This tool instructs or commands the robot arm to move in a circle.

    Args:
        ctx: The MCP server provided context 
    """
    print(f"Instructing cobot to move in a circle")
    robot_main.move_circle()
    return f"Instructing cobot to move in a circle"

@mcp.tool()
def scan_objects(ctx: Context) -> str:
    """Instruct cobot arm to scan for objects in front of it.

    This tool commands the robot arm to scan for the objects in front of it using object detection.

    Args:
        ctx: The MCP server provided context 
    """
    print(f"Instructing cobot to scan for objects")
    robot_main.move_to_scan()
    time.sleep(1)
    objs = latest_obj.find()
    labels = [obj["label"] for obj in objs]
    print(f"Len Objects: {len(labels)}", flush=True)
    return f"{labels}"

@mcp.tool()
def move_to_object(ctx: Context, item: str) -> str:
    """Instruct cobot arm to move to or track an item.

    This tool commands the robot arm to track or move to the X,Y position of a user specified item.

    Args:
        ctx: The MCP server provided context 
        item: The item to track
    """
    global CENTER_TOLERANCE_X, CENTER_TOLERANCE_Y, RETRY_COUNT
    logger.info(f"Instructing cobot to track {item}")
    try:
        x = np.inf
        y = np.inf
        retry_count = RETRY_COUNT
        while retry_count > 0:
            obj = latest_obj.find_one({"label": item})
            # logger.info(obj)
            if obj:
                x = obj["offset_x_mm"]
                y = obj["offset_y_mm"]
                if np.abs(x) < CENTER_TOLERANCE_X and np.abs(y) < CENTER_TOLERANCE_Y:
                    break
                # NOTE: For tool coordinate, image x-direction is negative cobot y-direction
                # NOTE: For tool coordinate, image y-direction is cobot x-direction
                logger.info(f"Moving cobot by x: {y}, y:{-x}")
                robot_main.move_by_xyz(x=y, y=-x, z=0)
            else:
                logger.info(f"{item} not found!")
                retry_count =- 1
        if retry_count == 0:
            logger.info(f"{item} not found!")
            return f"{item} not found!"
        else:
            return f"Reached {item}"
    except Exception as err:
        logger.info(err)
        return err
    
@mcp.tool()
def pickup_object(ctx: Context, item: str) -> str:
    """Instruct cobot arm to pickup an item.

    This tool commands the robot arm to pickup a user specified item and place it at a pre-determined position.

    Args:
        ctx: The MCP server provided context 
        item: The item to pickup
    """
    global DROP_X, DROP_Y, DROP_Z, MIN_Z, STEP_SIZE_Z
    logger.info(f"Instructing cobot to pickup and place {item}")
    try:
        status_msg = move_to_object(ctx=Context, item=item)
        if status_msg == f"Reached {item}":
            robot_main.pickup_n_place(x=DROP_X, y=DROP_Y, z=DROP_Z, min_z=MIN_Z, step_size=STEP_SIZE_Z)
        else:
            return status_msg
    except Exception as err:
        logger.info(err)
        return err


@mcp.tool()
def return_to_init(ctx: Context) -> str:
    """Instruct cobot arm to return to initial position.

    This tool commands the robot arm to return to its home/initial position.

    Args:
        ctx: The MCP server provided context 
    """
    print(f"Instructing cobot to return to initial position")
    robot_main.return_home()
    return f"Instructing cobot to return to initial position"

@mcp.tool()
def list_tools(ctx: Context) -> str:
    """List the tools available for cobot.

    Args:
        ctx: The MCP server provided context 
    """
    print(f"Listing tools")
    return f"I can instruct cobot to: 1) Return to Home position, 2) Scan for objects, 3) Move to an object, 4) Pickup an object, 5) Move in a circle, 6) Move in a square"

# @mcp.tool()
# def get_object(ctx: Context) -> int:
#     """Get the list of objects available for pickup by cobot.

#     This tool returns the list of objects available for pickup.

#     Args:
#         ctx: The MCP server provided context 
#     """
#     RESOURCES = ["ball", "book", "box"]
#     print(f"Available objects: {', '.join(RESOURCES)}")
#     return f"Available objects: {', '.join(RESOURCES)}"

async def main():
    await mcp.run_sse_async()

if __name__ == "__main__":
    # Access settings via the .settings attribute
    print(f"Configured Port: {mcp.settings.port}", flush=True) # Output: 8080
    # print(f"Duplicate Tool Policy: {mcp.settings.on_duplicate_tools}", flush=True) # Output: warn
    RobotMain.pprint('xArm-Python-SDK Version:{}'.format(version.__version__))
    print("SETUP DONE!")
    asyncio.run(main())