from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import uic

import sys
import cv2
import threading
import time
import pypylon.pylon as py
from pypylon import genicam
import sys
import cv2
import numpy as np
import pandas as pd
from SLABHIDDevice import HID_DEVICE_SUCCESS
import DevAddr as DA
import ConfigVal as CV
import time
import UsbCtrl
from LensCtrl import *
import DevAddr as DA
import LensAccess as LA
import LensInfo as LI
import DefVal as DV
import LensSetup as LS
import matplotlib.pyplot as plt
from PIL import Image
from LensConnect_Controller import *



class MainWindow(QWidget):

	DataUpdata1=pyqtSignal(int)
	DataUpdata2=pyqtSignal(int)
	DataUpdata3=pyqtSignal(str)
	# DataUpdata4=pyqtSignal(int)

	def __init__(self):
		super(MainWindow,self).__init__()
		self.M=[]
		self.Max1=0
		self.Text=[]
		self.index=0
		self.RawTime=[]
		self.ConInt=0

		
		self.VBL=QVBoxLayout()
	
		self.FeedLabel1=QLabel()
		self.VBL.addWidget(self.FeedLabel1)

		self.FeedLabel2=QLabel()
		self.VBL.addWidget(self.FeedLabel2)

		self.qle1 = QLineEdit(self)
		self.qle1.returnPressed.connect(self.onChanged1)
		self.VBL.addWidget(self.qle1)

		self.qle2 = QLineEdit(self)
		self.qle2.returnPressed.connect(self.onChanged2)
		self.VBL.addWidget(self.qle2)

		self.Cance1BTN=QPushButton("Cancel")
		self.Cance1BTN.clicked.connect(self.CancelFeed)
		self.VBL.addWidget(self.Cance1BTN)
		self.setLayout(self.VBL)
		
		self.Cance3BTN=QPushButton("APPLY")
		self.Cance3BTN.clicked.connect(self.APPLYFEED)
		self.VBL.addWidget(self.Cance3BTN)
		self.setLayout(self.VBL)

		self.Cance2BTN=QPushButton("Autofocus")

		self.VBL.addWidget(self.Cance2BTN)
		self.setLayout(self.VBL)

		self.DataUpdata3.connect(self.DataUpdate)
		
		self.Worker1=Woker1() ## 클래스 선언
		self.Worker1.ImageUpdata.connect(self.ImageUpdateSlot)
		self.Worker1.Data1.connect(self.DataUpdate)
		self.Worker1.start()		

		self.thread2=QThread()
		self.Woker2=Woker2() ## 클래스 선언
		self.Woker2.moveToThread(self.thread2)
		self.DataUpdata1.connect(self.Woker2.DataUpdateSlot1)
		self.Woker2.MoveUpdata.connect(self.TextUpdateSlot)
		self.Cance2BTN.clicked.connect(self.Woker2.Autofocusing)
		self.thread2.start()

	
	
	def ImageUpdateSlot(self, Image):
		self.FeedLabel1.setPixmap(QPixmap.fromImage(Image))
	
	def DataUpdate(self,Data):

		if len(self.Text)==5:
			self.index==0
			self.M.extend([Data])
			Max2=max(self.M)
			curTime = time.time()
			if len(self.M)==1:
				self.Fst_Time=curTime

			if Max2 > self.Max1:
				self.RawTime.extend([curTime])
				print(Max2,len(self.M),curTime)
				self.Max1=Max2

		if len(self.Text)==3 and self.index==0:
			self.M=[]
			IntTime=self.RawTime[-1]-self.Fst_Time
			self.ConInt=2640+(IntTime/38.5)*2400
			# self.DataUpdata4.emit(self.ConInt)
			print(IntTime)
			print(self.ConInt)
			Max2=0
			self.Max1=0
			self.index=+1
			self.RawTime=[]
			self.index==0
	

	def TextUpdateSlot(self,Text):
		self.Text=Text
		self.FeedLabel2.setText(Text)
		self.FeedLabel2.setAlignment(Qt.AlignCenter)
		print(Text)
	
	def APPLYFEED(self):
		enter=int(self.ConInt)
		print(enter)
		self.DataUpdata1.emit(enter)

	def onChanged1(self):
		Value_Changed1=int(self.qle1.text())
		self.DataUpdata1.emit(Value_Changed1)

	def onChanged2(self):
		Value_Changed2=int(self.qle2.text())
		self.DataUpdata2.emit(Value_Changed2)
	
	def CancelFeed(self):
		self.Worker1.stop()

class Woker1(QThread):

	ImageUpdata=pyqtSignal(QImage)
	Data1=pyqtSignal(float)
	
	def __init__(self):
		super(Woker1,self).__init__()

	def run(self):
		tl_factory = py.TlFactory.GetInstance()
		devices = tl_factory.EnumerateDevices()
		
		for device in devices:
			print(device.GetFriendlyName())
		tlf = py.TlFactory.GetInstance()
		camera = py.InstantCamera(tlf.CreateDevice(devices[0]))
	
		camera.Open()
		
		# Camera Setting ##
		camera.ExposureTime=20000
		camera.Gain=10
		camera.TriggerSelector='FrameStart'

		# Grabing Continusely (video) with minimal delay
		camera.StartGrabbing(py.GrabStrategy_LatestImageOnly) 
		converter = py.ImageFormatConverter()

		# converting to opencv bgr format
		converter.OutputPixelFormat = py.PixelType_BGR8packed
		converter.OutputBitAlignment = py.OutputBitAlignment_MsbAligned
		index=0
		fps=0
		fps_str = "FPS : %0.3f" %fps
		prevTime = time.time()

		while camera.IsGrabbing():

			grabResult = camera.RetrieveResult(5000, py.TimeoutHandling_ThrowException)


			if grabResult.GrabSucceeded():
				index+=1
				image = converter.Convert(grabResult)
				img = image.GetArray()
				Image=cv2.cvtColor(img,cv2.COLOR_BGR2RGB)

				curTime = time.time()	# current time
				if index==60:
					fps = 1 / ((curTime - prevTime)/60)
					prevTime = curTime
					index=0

				fps_str = "FPS : %0.2f" %fps
				ROI_Img= Image[500:700,800:1120]
				laplacian_var = round(cv2.Laplacian(ROI_Img, cv2.CV_64F).var(),2)
				cv2.putText(Image, 'Focus level: '+str(float(laplacian_var)), (1300, 100),cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0),3)
				cv2.putText(Image, fps_str, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0),3)
				ConvertToQtFormat=QImage(Image.data,Image.shape[1],Image.shape[0],QImage.Format_RGB888)
				Pic= ConvertToQtFormat.scaled(1200,960, Qt.KeepAspectRatio)
				self.ImageUpdata.emit(Pic)
				self.Data1.emit(laplacian_var)

	def stop(self):
		self.ThreadActive=False
		self.quit()


class Woker2(QObject):
		
	MoveUpdata=pyqtSignal(str)

	def __init__(self):
		super(Woker2,self).__init__()
		self.M=[] 

	def DataUpdateSlot1(self,data):

		Move=data
		UsbConnect(0)
		FocusParameterReadSet()
		print(LensCtrl.focusCurrentAddr)
		print(LensCtrl.focusMinAddr)
		print(LensCtrl.focusMaxAddr)
		print(LensCtrl.focusSpeedPPS)
		FocusMove(Move)
		print
		if Move==0:
			FocusInit() 
	
	def Autofocusing(self):
		UsbConnect(0)
		FocusParameterReadSet()
		FocusMove(LensCtrl.focusMinAddr)
		time.sleep(1)
		prevTime = time.time()	
		self.MoveUpdata.emit("Start")
		FocusMove(LensCtrl.focusMaxAddr)
		curTime = time.time()	
		self.MoveUpdata.emit("End")
		intTime=curTime-prevTime
		print(intTime)
		FocusInit() 

	def stop(self):
		self.quit()


if __name__ == '__main__':
	App = QApplication(sys.argv)
	Root = MainWindow()
	Root.show()
	sys.exit(App.exec())
  
    