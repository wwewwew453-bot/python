import cv2
from PIL import Image


IMAGE_PATH = 'cat6.jpg'
cat_face_cascade = cv2.CascadeClassifier('haarcascade_frontalcatface_extended.xml')

image = cv2.imread(IMAGE_PATH)
cat_face = cat_face_cascade.detectMultiScale(image)

print(cat_face)

cat = Image.open(IMAGE_PATH).convert('RGBA')
glasses =Image.open('glasses.png').convert('RGBA')

for x,y,w,h in cat_face:
    # cv2.rectangle(image,(x,y),(x+w, y+h),(0,0,255), 3)
    glasses = glasses.resize((w, h//3))
    cat.paste(glasses, (x, int(y + h / 4)), glasses)

cat.save('new_cat.png')

new_image = cv2.imread('new_cat.png')
cv2.imshow('Cat', new_image)
cv2.waitKey()
