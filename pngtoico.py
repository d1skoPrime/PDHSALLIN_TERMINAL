from PIL import Image

img = Image.open("logo.png")
img.save("icon.ico", sizes=[(16,16), (32,32), (48,48), (256,256)])
