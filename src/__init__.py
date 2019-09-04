import os, sys


#not sure if necessary, not even printing the append to path things
#everything is working from the local files when importing the modiles so..
#guess you can delete and ignore all the __init__.py objects including this one
#I was just trying fixing the import errors from pylint but figured out it was a
#pylint config path was not set up in my workspace here

#might be better to put this file somewhere else, maybe dandere2x.py?



#[tremx] let's add our project root folder temporary to system path 

#this is the current file dir (in my case /home/tremeschin/github/dandere2x-1.4.2/src) 
#and that's what we want cause it's flexible
ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + os.path.sep

# a dictionary of current file folder structure
modules_dic_path = {
    "dandere2xlib": [
        "core", "utils"
    ],
    "wrappers": [
        "ffmpeg", "frame", "waifu2x"
    ]
}

path_to_add = [ROOT_DIR]

for key in modules_dic_path:
    path_to_add.append(os.path.join(ROOT_DIR, key))

for key in modules_dic_path:
    for subdir in modules_dic_path[key]:
        path_to_add.append(os.path.join(ROOT_DIR, key, subdir))


for path in path_to_add:
    print("Adding to path:", path)
    sys.path.append(path)

#done, no more dumb import errors I was getting eventhough it was all running fine
print(sys.path)
####################################################################################################################################
