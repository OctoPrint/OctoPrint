try:
	import comtypes.client as cc
	cc.GetModule('taskbarlib.tlb')
	import comtypes.gen.TaskbarLib as tbl

	ITaskbarList3 = cc.CreateObject("{56FDF344-FD6D-11d0-958A-006097C9A090}", interface=tbl.ITaskbarList3)
	ITaskbarList3.HrInit()

	#Stops displaying progress and returns the button to its normal state. Call this method with this flag to dismiss the progress bar when the operation is complete or canceled.
	TBPF_NOPROGRESS = 0x00000000
	#The progress indicator does not grow in size, but cycles repeatedly along the length of the taskbar button. This indicates activity without specifying what proportion of the progress is complete. Progress is taking place, but there is no prediction as to how long the operation will take.
	TBPF_INDETERMINATE = 0x00000001
	#The progress indicator grows in size from left to right in proportion to the estimated amount of the operation completed. This is a determinate progress indicator; a prediction is being made as to the duration of the operation.
	TBPF_NORMAL = 0x00000002
	#The progress indicator turns red to show that an error has occurred in one of the windows that is broadcasting progress. This is a determinate state. If the progress indicator is in the indeterminate state, it switches to a red determinate display of a generic percentage not indicative of actual progress.
	TBPF_ERROR = 0x00000004
	#The progress indicator turns yellow to show that progress is currently stopped in one of the windows but can be resumed by the user. No error condition exists and nothing is preventing the progress from continuing. This is a determinate state. If the progress indicator is in the indeterminate state, it switches to a yellow determinate display of a generic percentage not indicative of actual progress.
	TBPF_PAUSED = 0x00000008
except:
	#The taskbar API is only available for Windows7, on lower windows versions, linux or Mac it will cause an exception. Ignore the exception and don't use the API
	ITaskbarList3 = None

def setBusy(frame, busy):
	if ITaskbarList3 != None:
		if busy:
			ITaskbarList3.SetProgressState(frame.GetHandle(), TBPF_INDETERMINATE)
		else:
			ITaskbarList3.SetProgressState(frame.GetHandle(), TBPF_NOPROGRESS)

def setPause(frame, pause):
	if ITaskbarList3 != None:
		if pause:
			ITaskbarList3.SetProgressState(frame.GetHandle(), TBPF_PAUSED)
		else:
			ITaskbarList3.SetProgressState(frame.GetHandle(), TBPF_NORMAL)

def setProgress(frame, done, total):
	if ITaskbarList3 != None:
		ITaskbarList3.SetProgressState(frame.GetHandle(), TBPF_NORMAL)
		ITaskbarList3.SetProgressValue(frame.GetHandle(), done, total)
