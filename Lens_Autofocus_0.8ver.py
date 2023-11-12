
import numpy as np
import pandas as pd
import cv2
from pypylon import pylon
from SLABHIDDevice import HID_DEVICE_SUCCESS
import DevAddr as DA
import ConfigVal as CV
import time
import UsbCtrl
import LensCtrl
import DevAddr as DA
import LensAccess as LA
import LensInfo as LI
import DefVal as DV
import LensSetup as LS
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

def UsbConnect(deviceNumber):
	global usbOpen_flag
	global withZoom
	global withFocus
	global withIris
	global withOptFil
	retval = UsbCtrl.UsbOpen(deviceNumber)
	if (retval != DV.RET_SUCCESS):
		print(retval)
		return retval
	
	retval = UsbCtrl.UsbSetConfig()
	if (retval != DV.RET_SUCCESS):
		print(retval)
		return retval

	retval, capabilities = LensCtrl.CapabilitiesRead()
	LensCtrl.Status2ReadSet()

	if (capabilities & CV.ZOOM_MASK):
		LensCtrl.ZoomParameterReadSet()
		if (LensCtrl.status2 & CV.ZOOM_MASK == DV.INIT_COMPLETED):
			LensCtrl.ZoomCurrentAddrReadSet()
		withZoom = True

	if (capabilities & CV.FOCUS_MASK):
		LensCtrl.FocusParameterReadSet()
		if (LensCtrl.status2 & CV.FOCUS_MASK == DV.INIT_COMPLETED):
			LensCtrl.FocusCurrentAddrReadSet()
		withFocus = True

	if (capabilities & CV.IRIS_MASK):
		LensCtrl.IrisParameterReadSet()
		if (LensCtrl.status2 & CV.IRIS_MASK == DV.INIT_COMPLETED):
			LensCtrl.IrisCurrentAddrReadSet()
		withIris = True

	if (capabilities & CV.OPT_FILTER_MASK):
		LensCtrl.OptFilterParameterReadSet()
		if (LensCtrl.status2 & CV.OPT_FILTER_MASK == DV.INIT_COMPLETED):
			LensCtrl.OptFilterCurrentAddrReadSet()
		withOptFil = True
	usbOpen_flag = True
	retval = 0
	return retval

def WaitCalc(moveValue, speedPPS):
	waitTime = CV.WAIT_MAG *moveValue / speedPPS
	if (CV.MINIMUM_WAIT > waitTime):
		waitTime = CV.MINIMUM_WAIT
	return waitTime

def FocusParameterReadSet():
	global focusMinAddr
	global focusMaxAddr
	global focusSpeedPPS
	retval, focusMinAddr = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_MECH_STEP_MIN)
	if (retval != HID_DEVICE_SUCCESS):
		return retval
	retval, focusMaxAddr = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_MECH_STEP_MAX)
	if (retval != HID_DEVICE_SUCCESS):
		return retval
	retval, focusSpeedPPS = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_SPEED_VAL)
	if (retval != HID_DEVICE_SUCCESS):
		return retval
	return retval


def StatusWait(segmentOffset, statusMask, waitTime):
	tmp = 0
	readStatus = 0
	while ((readStatus & statusMask) != statusMask):
		retval, data = UsbCtrl.UsbRead2BytesInt(segmentOffset)
		if (retval != HID_DEVICE_SUCCESS):
			return retval
		readStatus = data
		tmp += 1
		if (tmp >= CV.LOW_HIGH_WAIT):
			return CV.LOWHI_ERROR
	tmp = 0
	readStatus = 0xFF
	while ((readStatus & statusMask) != 0):
		retval, data = UsbCtrl.UsbRead2BytesInt(segmentOffset)
		if (retval != HID_DEVICE_SUCCESS):
			return retval
		readStatus = data
		tmp += 1
		if (tmp >= waitTime):
			return CV.HILOW_ERROR
		time.sleep(0.001)
	return retval

def Status2ReadSet():
	global status2
	retval, status2 = UsbCtrl.UsbRead2BytesInt(DA.STATUS2)
	return retval, status2

def FocusInit():
	global focusMaxAddr
	global focusMinAddr
	global focusSpeedPPS
	global focusCurrentAddr
	waitTime = WaitCalc((focusMaxAddr - focusMinAddr), focusSpeedPPS)
	retval = UsbCtrl.UsbWrite(DA.FOCUS_INITIALIZE, CV.INIT_RUN_BIT)
	if (retval == HID_DEVICE_SUCCESS):
		retval = StatusWait(DA.STATUS1, CV.FOCUS_MASK, waitTime)
		if (retval == HID_DEVICE_SUCCESS):
			retval, focusCurrentAddr = UsbCtrl.UsbRead2BytesInt(DA.FOCUS_POSITION_VAL)
			if (retval == HID_DEVICE_SUCCESS):
				Status2ReadSet()
				return retval
	return retval

def DeviceMove(segmentOffset, addrData, mask, waitTime):
	retval = UsbCtrl.UsbWrite(segmentOffset, addrData)
	if (retval == HID_DEVICE_SUCCESS):
		retval = StatusWait(DA.STATUS1, mask, waitTime)
		if (retval == HID_DEVICE_SUCCESS):
			retval, data = UsbCtrl.UsbRead2BytesInt(segmentOffset)
			if (retval != HID_DEVICE_SUCCESS):
				return retval, addrData
			addrData = data
	return retval, addrData

def FocusMove(addrData):
	global focusCurrentAddr
	global focusSpeedPPS
	moveVal = abs(addrData - focusCurrentAddr)
	waitTime = WaitCalc(moveVal, focusSpeedPPS)
	retval, data = DeviceMove(DA.FOCUS_POSITION_VAL, addrData, CV.FOCUS_MASK, waitTime)
	if (retval == HID_DEVICE_SUCCESS):
		focusCurrentAddr = data
	return retval

def UsbDisconnect():
	global usbOpen_flag
	global withZoom
	global withFocus
	global withIris
	global withOptFil

	UsbCtrl.UsbClose()
	usbOpen_flag = False
	withZoom = False
	withFocus = False
	withIris = False
	withOptFil = False
	


def empty(pos):
    pass

def Movei():
	pos=input("이동거리를 입력하세요")
	return int(pos)

def StdDev(image):
    Mean, Stdev =cv2.meanStdDev(image)
    return float(Stdev)

UsbConnect(0)
FocusParameterReadSet()
FocusInit()
print(focusCurrentAddr)


# conecting to the first available camera
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

# Grabing Continusely (video) with minimal delay
camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly) 
converter = pylon.ImageFormatConverter()

# converting to opencv bgr format
converter.OutputPixelFormat = pylon.PixelType_BGR8packed
converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
name='title'

# cv2.namedWindow(name, cv2.WINDOW_NORMAL)
# cv2.createTrackbar('Focuse_Move',name,0,3000,empty)
# cv2.setTrackbarPos('Focuse_Move',name,focusCurrentAddr)



i=500
W=np.array([[0,0]])

while camera.IsGrabbing():
	grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
 
	if grabResult.GrabSucceeded():
		# Access the image data
		image = converter.Convert(grabResult)
		img = image.GetArray()
		img_Gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

		if i <=2000 :
			i+=20
			FocusMove(i)
			cv2.waitKey(1000)
			cv2.imshow('title',img_Gray)
			U=np.array([[i,StdDev(img_Gray)]])
			W=np.concatenate((W,U),axis=0)
			print(W)
			continue		
		index=np.argmax(W[:,1])
		M,Q =W[index]
		if not M==focusCurrentAddr:
			FocusMove(int(M))
			print(M)
		k = cv2.waitKey(1)
		if k == ord('q'):
			print("사용자 입력에 의해 종료합니다.")
			break
		cv2.imshow('title',img)
   
	grabResult.Release()
	
# Releasing the resource    
camera.StopGrabbing()
cv2.destroyAllWindows()


# while camera.IsGrabbing():
#     	grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
 
# 	if grabResult.GrabSucceeded():
# 		# Access the image data
# 		image = converter.Convert(grabResult)
# 		img = image.GetArray()
# 		img_Gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
# #		Move=cv2.getTrackbarPos('Focuse_Move','title')
# 		# cv2.imshow('title',img)
# 		# P=focusCurrentAddr-Move
# 		# if not P == 0:
# 		# 	FocusMove(Move)
# 		k = cv2.waitKey(1)
# 		if k == ord('q'):
# 			print("사용자 입력에 의해 종료합니다.")
# 			break
# 		if k== ord('w'):
# 		i=
# 			for i in range(2000,500,-20):
# 				FocusMove(i)
# 				cv2.waitKey(1000)
# 				cv2.imshow('title',img)
# 			continue
   
# 	grabResult.Release()
	
# # Releasing the resource    
# camera.StopGrabbing()
# cv2.destroyAllWindows()