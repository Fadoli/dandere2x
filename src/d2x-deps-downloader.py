import requests, zipfile, json, time, wget, os

ROOT = os.path.dirname(os.path.abspath(__file__))


# get the release stuff

print("\n Getting the repo releases..")

data = requests.get("https://api.github.com/repos/aka-katto/dandere2x_externals_static/releases").json()

release_names = {}

for count, release in enumerate(data):
    release_names[count] = release['name'] 


# get the user input

while True:
    print("\n\n  Hi, please select the version you want to download")
    print(  "   (can be a csv input like: 0,1,2)\n")

    for index in release_names:
        print(index, " - ", release_names[index])

    uinput = input("\n>> ")

    try:
        todownload = []
        uinput = uinput.split(",")

        for index in uinput:
            todownload.append(release_names[int(index)])
            
        break

    except Exception:
        pass



# get the download links

download_links = {}

for relname in todownload:
    
    for count, release in enumerate(data):
        if release['name'] == relname:
            download_links[release['name']] = release['assets'][0]['browser_download_url']



# download them

eta = 1
currentrelease = ""

def bar_custom(current, total, width=80):
    global currentrelease, startdownload


    #current       -     time.time() - startdownload 
    #total-current -     eta

    #eta ==   (total-current)*(time.time()-startdownload)) / current

    try: # div by zero
        eta = int(( (time.time() - startdownload) * (total - current) ) / current)
    except Exception:
        eta = 0

    avgdown = ( current / (time.time() - startdownload) ) / 1024

    currentpercentage = int(current / total * 100)
    
    print("\r Downloading release [{}]: [{}%] [{:.2f} MB / {:.2f} MB] ETA: [{} sec] AVG: [{:.2f} kB/s]".format(currentrelease, currentpercentage, current/1024/1024, total/1024/1024, eta, avgdown), end='', flush=True)
        


print('\n\n  Now starting the downloads..\n')

for name, link in download_links.items():
    
    currentrelease = name.replace(" - Static Externals for Dandere2x", "")
    
    savepath = ROOT + os.path.sep + name + ".zip"

    if not os.path.exists(savepath):
        startdownload = time.time()
        wget.download(link, savepath, bar=bar_custom)
        print("\n")
    else:
        print("File " + name + " already downloaded.")

    # extract them

    print("  Extracting the release " + currentrelease + "...", end='')

    with zipfile.ZipFile(savepath, 'r') as zip_ref:
        zip_ref.extractall(ROOT)
    
    print(" finished!!\n\n")

    os.remove(savepath)
