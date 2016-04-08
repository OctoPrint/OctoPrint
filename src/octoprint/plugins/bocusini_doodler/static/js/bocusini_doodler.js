$(function () {
	function BocusiniDoodlerViewModel(parameters) {
		var self = this;

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
				self.ps.pause();
				self.control.sendHomeCommand(['x', 'y']);
			}
			if (self.ps.isPaused()) {
				self.control.sendHomeCommand(['x', 'y']);
				self.ps.pause();
			}
		};

		self.cancel = function () {
			self.ps.cancel();
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
});
