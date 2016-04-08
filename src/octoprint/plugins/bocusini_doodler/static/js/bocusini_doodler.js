$(function () {
	function BocusiniDoodlerViewModel(parameters) {
		var self = this;
		var replace = 0;
		self.loginState = parameters[0];
		self.ps = parameters[1]; // printerState
		self.settings = parameters[2];
		self.control = parameters[3];

		self.tempOffTimeout = 10*60*1000; // 10 min in milliseconds. TODO: put into settings.

		self.actualTemp = ko.observable('-');
		self.targetTemp = ko.observable('-');
		self.isPreheating = ko.computed(function(){
			var heating = !isNaN(self.targetTemp()) && !isNaN(self.actualTemp()) && (self.targetTemp() - self.actualTemp() > 1);
			return self.ps.isPrinting() && heating; 
		});

//modification
		self.isCooling = ko.computed(function(){
			var cooling = !isNaN(self.targetTemp()) && !isNaN(self.actualTemp()) && (self.actualTemp() > self.targetTemp());
			return self.ps.isPrinting() && cooling; 
		});
		self.isCold = ko.computed(function(){
			var cold = (self.targetTemp()==0);
			return cold; 
		});
		self.isWarm = ko.computed(function(){
			var warm = (self.targetTemp()>0);
			return warm; 
		});
//end_modification

		self.progressString = self.ps.progressString;



		self.user_is_admin = function () {
			return document.location.hash === '#admin';
		};
		//self.user_is_admin = self.loginState.isAdmin;

		self.hide_doodler = function () {
			$('body').removeClass('doodler_active');
		};

		self.pause = function () {
			console.log('pause');
			if (self.ps.isPrinting()) {
				self.sendRetractCommand(1);
				self.control.sendCustomCommand({ commands: ["G28 Y0"] });
				self.ps.pause();
				self.control.sendHomeCommand(['x', 'y']);


				if (confirm("Replace the cartridge?") == true)
	  			{
				self.control.sendCustomCommand({ commands: ["G28 Z0"] });
				self.sendRetractCommand(500);
				replace = 1;
				}

			}


			if (self.ps.isPaused()) {
				if (replace == 1)
				{
				self.control.sendCustomCommand({commands: ["G92 E0"]});
				// alert("Cartridge changed");
				var myVar;
				alert("Cartridge changed. Please wait 5 minutes");
				myFunction();
					function myFunction() {
   				 		myVar = setTimeout(alertFunc, 300000);
					}
					function alertFunc() {
						alert("Ready");
						self.ps.pause();
						replace = 0;
					}
	
				}
				// self.control.sendHomeCommand(['x', 'y']);
				else {
				self.control.sendCustomCommand({commands: ["G92 E1"]});
				self.control.sendCustomCommand({commands: ["G92 E0"]});
				self.ps.pause();
				}
			}
		};

		self.cancel = function () {
			self.sendRetractCommand(3);
			self.ps.cancel();
//modification		
			self.control.sendCustomCommand({ commands: ["G28 Y0"] });
			self.control.sendCustomCommand({commands: ["G28"]});
//end_modification
		};
		self.start = function () {
			if ($('body').hasClass('doodler_active')) {
				console.log('starting doodle print');
				if (_points.length > 2) {
					var filename = self._doodler_get_filename();
					self.saveDoodleThumb(filename);
					
					// we put the gcode generation in a little delay
					// so that for example the print button is disabled right away
					clearTimeout(gcodeGenerateDelayer);
					gcodeGenerateDelayer = setTimeout(function() {

						var gcode = generate_gcode();
						if(gcode.length > 0) {				

							// upload generated gcode via OctoPrints File API
							var data = new FormData();
							var blob = new Blob([gcode.join("\n")], {type: "text/plain"});
							data.append("file", blob, filename);
							data.append("print", true);

							jQuery.ajax({
								url: API_BASEURL + "files/local",
								data: data,
								dataType: 'json',
								cache: false,
								contentType: false,
								processData: false,
								type: 'POST',
								success: self.doodler_gcode_upload_done,
								fail: self.doodler_gcode_upload_fail,
								progress: self.doodler_gcode_upload_progress
							});
						}
					}, 50);
				}
			} else {
				console.log("Print without selection - not specified yet.");
			}
		};
//modification

        self.sendExtrudeCommand = function (amount) {
            self._sendECommand(1, amount);
        };

        self.sendRetractCommand = function (amount) {
            self._sendECommand(-1, amount);
        };

        self._sendECommand = function (dir, amount) {
			var length;
			if(typeof amount === 'undefined' || isNaN(amount)){
				length = self.extrusionAmount();
			} else {
				length = amount;
			}
            if (!length) length = self.settings.printer_defaultExtrusionLength();

            self.sendToolCommand({
                command: "extrude",
                amount: length * dir
            });
        };

        self.sendSelectToolCommand = function (data) {
            if (!data || !data.key()) return;

            self.sendToolCommand({
                command: "select",
                tool: data.key()
            });
        };
	
	self.sendPrintHeadCommand = function (data) {
            $.ajax({
                url: API_BASEURL + "printer/printhead",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data)
            });
        };


        self.sendToolCommand = function (data) {
            $.ajax({
                url: API_BASEURL + "printer/tool",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data)
            });
        };

//end modification
		
		
		
		
		self.init_calibration = function(){
			self._zOffset = 0;
			self.control.sendHomeCommand(['x','y']);	
			self.control.sendHomeCommand(['z']);	
			console.log('init calibration, Z Offset: 0');
			$('#calibration_step1').removeClass('active');
			$('#calibration_step2').addClass('active');
		};
		
		self.do_calibration = function(amount){
			self._zOffset += amount;
			self.control.sendJogCommand('z',1, amount);
			console.log("Z Offset", self._zOffset);
		};
		
		self.finish_calibration = function(){
			var cmd = "M211Z"+(self._zOffset*-1);
			self.control.sendCustomCommand({
				commands: [cmd,"M500" , "G28"]
			});	
//modification
			// msgBox("Calibration successful");
			alert("Calibration successful");
//end_modification
			$('.calibration_tab').removeClass('active');
			$('#calibration_step1').addClass('active');
		};

		self.doodler_gcode_upload_done = function(payload){
			// start OctoPrint streaming after upload is done
			console.log("gcode_upload_done", payload);
		}
		self.doodler_gcode_upload_fail = function(payload){
			console.log("gcode_upload_fail", payload);
		}
		self.doodler_gcode_upload_progress = function(payload){
			console.log("gcode_upload_progress", payload);
		}

		self._doodler_get_filename = function(){
			var date = new Date();

			var month = date.getMonth() + 1;
			var day = date.getDate();
			var hour = date.getHours();
			var min = date.getMinutes();
			var sec = date.getSeconds();

			month = (month < 10 ? "0" : "") + month;
			day = (day < 10 ? "0" : "") + day;
			hour = (hour < 10 ? "0" : "") + hour;
			min = (min < 10 ? "0" : "") + min;
			sec = (sec < 10 ? "0" : "") + sec;

			var str = "bocusini_doodle_" + date.getFullYear() + "-" + month + "-" + day + "_" +  hour + "." + min + "." + sec + ".gco";

			return str;
		}

		self.saveDoodleThumb = function(filename){
			filename = filename.split('.gco')[0]+'.jpg'
			var canvas = document.getElementById("mycanvas");
			//var dataURI = canvas.toDataURL("image/jpeg", 0.7);
			var dataURI = canvas.toDataURL("image/png");
			var binary = atob(dataURI.split(',')[1]), array = [];
	        for(var i = 0; i < binary.length; i++) array.push(binary.charCodeAt(i));
		    //var img = new Blob([new Uint8Array(array)], {type: "image/jpeg"});
		    var img = new Blob([new Uint8Array(array)], {type: "image/png"});
			var data = new FormData();
			data.append("file",  img, filename);

			jQuery.ajax({
				url: "/plugin/bocusini_doodler/thumb",
				data: data,
//				dataType: 'json',
				cache: false,
				contentType: false,
				processData: false,
				type: 'POST',
				success: function(){ console.log('doodle thumbnail uploaded'); }
			});
		};
		

		self.onStartup = function () {
			$('body').addClass('doodler_active');
			setTimeout(function(){
				$('#bocusini_nav a[href="#bocusini_calibration"]').tab('show');
			},1000); // Hack. switch tab after a short timeout.
		};

		// grab temperature
		self.fromCurrentData = function (data) {
			if (data.length === 0)
				return;
			if (typeof data['temps'] !== 'undefined') {
				if (typeof data['temps'][0] !== 'undefined') {
					if (typeof data['temps'][0]['tool0'] !== 'undefined') {
						self.targetTemp(data['temps'][0]['tool0']['target']);
						self.actualTemp(data['temps'][0]['tool0']['actual']);
					}
				}
			}
		};
		
		self.switchTempOffDelayed = function(event){
			clearTimeout(self.heatingTimeout); // clear old timeouts
			self.heatingTimeout = setTimeout(function(){
				console.log("Heating switched off due inactivity.");
				self._sendTempCommand(0);
			}, self.tempOffTimeout);
		};
		
		// however the print ends, switch off after some time.
		self.onEventPrintDone = self.switchTempOffDelayed;
		self.onEventPrintFailed = self.switchTempOffDelayed;
		self.onEventPrintCancelled = self.switchTempOffDelayed;
		
		self.onEventConnected = function(){
			self._sendTempCommand(60); // start preheating directly after connect.
			self.switchTempOffDelayed();
		};
		self.onEventPrintStarted = function(){
			if(typeof self.heatingTimeout !== 'undefined') {
				clearTimeout(self.heatingTimeout);
			}
		};
		
		self._sendTempCommand = function(temp, successCb, errorCb){
			var t = parseInt(temp)
			var data = {
				command: "target",
				targets: {tool0: t}
			};

		    $.ajax({
                url: API_BASEURL + "printer/tool",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function() { if (successCb !== undefined) successCb(); },
                error: function() { if (errorCb !== undefined) errorCb(); }
            });	
		};
		
		self._tempStr = function(val) {
			if (typeof val === 'undefined' || isNaN(val)) return '-';
			else return val + '°C';
		};

	}

	// view model class, parameters for constructor, container to bind to
	ADDITIONAL_VIEWMODELS.push([
		BocusiniDoodlerViewModel,
		["loginStateViewModel", "printerStateViewModel", "settingsViewModel", "controlViewModel"],
		["#system_buttons", "#bocusini_printerstate_buttons", '#bocusini_statemonitor', '#bocusini_calibration']
	]);


//*****************************
//  Custom Alert Box
//  Free to use with credits in tact.
//  Written By Adam Matthews aka Basscyst
//	AdamDMatthews@Gmail.com
//*****************************
function msgBox(msg,hdr){
	if(!document.getElementById('alerts')){
		var div=document.createElement('div');
		div.setAttribute('id','alerts');
		document.body.appendChild(div);
	}
	var div=document.createElement('div');
	div.className="alertbox";
	var h3=document.createElement('h3');
	h3.className="alerttitle";
	var p=document.createElement('p');
	p.className="alerttxt";
	var footdiv=document.createElement('p');
	footdiv.className="alertfoot";
	div.appendChild(h3);
	div.appendChild(p);
	div.appendChild(footdiv);
	var but=document.createElement('input');
	but.setAttribute('type','button');
	but.className='alertbut';
	but.setAttribute('value','OK');
	footdiv.appendChild(but);
	var hdr=(hdr) ? hdr : "Alert!";
	h3.appendChild(document.createTextNode(hdr));
	var cut=msg.split("\n");
	var len=cut.length;
	p.appendChild(document.createTextNode(cut[0]));
	for(var i=1;i<len;i++){	
		p.appendChild(document.createElement('br'));
		p.appendChild(document.createTextNode(cut[i]));
	}
	document.getElementById('alerts').appendChild(div);
	window.onscroll=function(){
		placeAlerts();	
	}
	window.onresize=function(){
		placeAlerts();	
	}
	placeAlerts();
}
var posX;
var posY;
function mouseXY(e){
	if (!e){
		var e = window.event;	
	}
	if (e.clientX)
	{
	     posX = e.clientX + document.documentElement.scrollLeft;
	     posY = e.clientY + document.documentElement.scrollTop;
	}
	else
	{
	     posX = Math.max(e.pageX,0);
	     posY = Math.max(e.pageY,0);
	}
	var coord=new Array();
	return coord;
}
if(document.captureEvents){
	document.captureEvents(Event.MOUSEMOVE)
}
function placeAlerts(){
	var alerts=document.getElementById('alerts').getElementsByTagName('div');
	var len=alerts.length;
	var x=0;
	var y=300;
	var w=document.body.clientWidth;
	var h=document.body.clientHeight;
	for(var i=0;i<len;i++){
		alerts[i].style.zIndex=i+100;
		alerts[i].getElementsByTagName('h3')[0].onmousedown="";
		alerts[i].getElementsByTagName('input')[0].onclick="";
		
		if(window.pageYOffset){
				alerts[i].style.top=y+(window.pageYOffset)+'px';
			}else{
				alerts[i].style.top=y+(document.documentElement.scrollTop)+'px';
			}
		alerts[i].style.left=(w / 2)- (343 / 2) + x +'px';;
		x=x+15;
		y=y+15;
		if(i==len-1){
			var h3=alerts[i].getElementsByTagName('h3')[0];
			var but=alerts[i].getElementsByTagName('input')[0];
			but.onclick=function(){
				this.parentNode.parentNode.parentNode.removeChild(this.parentNode.parentNode);	
				var alerts=document.getElementById('alerts').getElementsByTagName('div');
				if(alerts.length==0){
					window.onscroll="";
				}
				placeAlerts();
			}
			h3.onmousedown=function(event){
				this.parentNode.setAttribute('id','active_alert');
				var event=(event)?event:arguments[0];
					mouseXY(event);
				start_x=posX;
				start_left=document.getElementById('active_alert').style.left.replace('px','');
				adjust=posX-start_left;
				document.onmousemove=function(event){
					var event=(event)?event:arguments[0];
					mouseXY(event);
					var obj=document.getElementById('active_alert');
					obj.style.left=posX-adjust+'px';
					obj.style.top=posY-5+'px';
				};
			}
			h3.onmouseup=function(){
				document.onmousemove="";
				this.parentNode.setAttribute('id','');
			}	
		}
	}	
}

//*****************************
// Custom Alert Box
// end_modification
//*****************************

});