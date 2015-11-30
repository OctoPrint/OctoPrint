/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

var API = function() {
	var className = 'API';
	var _wifiboxURL = 'http://10.10.0.1/';
	var _wifiboxCGIBinURL = 'http://10.10.0.1/cgi-bin/myapi';
	var _timeoutTime = 10000;
	var _isBusy = false;

	function setURL(url,cgiUrl) {
		_wifiboxURL = url;
		_wifiboxCGIBinURL = cgiUrl || url;
	}

	function post(cmd,data,success,fail) {
		_isBusy = true;
		$.ajax({
			url: _wifiboxURL + cmd,
			type: "POST",
			data: data,
			dataType: 'json',
			timeout: _timeoutTime,
			success: function(response){
				_isBusy = false;
				if(response.status == "error" || response.status == "fail") {
					console.log(className,'post fail',cmd)
					if (fail) fail(response);
				} else {
					if (success) success(response.data);
					else console.log(className,'post:',cmd,'success cb undefined')
				}
			}
		}).fail(function(jqXHR, textStatus) {
			_isBusy = false;
			console.log(className,'post fail',cmd,jqXHR,textStatus);
			if (fail) fail(jqXHR,textStatus);
		});
	}

	function get(cmd,data,success,fail) {
		_isBusy = true;
		$.ajax({
			url: _wifiboxURL + cmd,
			type: "GET",
			data: data,
			dataType: 'json',
			timeout: _timeoutTime,
			success: function(response) {
				_isBusy = false;
				if (response.status == "error" || response.status == "fail") {
					console.log(className,'get fail',cmd,response);
					if (fail) fail(response);
				} else {
					if (success) success(response.data);
					else console.log(className,'get:',cmd,'success cb undefined')
				}
			}
		}).fail(function() {
			_isBusy = false;
			console.log(className,'get fail',cmd);
			if (fail) fail();
		});
	}

	function getBusy() {
		return _isBusy;
	}

	return {
		get: get,
		post: post,
		getBusy: getBusy,
		setURL: setURL,
	}

}();


/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

function ConfigAPI() {
	var className = 'ConfigAPI';

	function init() {
		console.log(className,'init is deprecated');
	}

	function loadAll(success,fail) {
		API.get('config/all',{},success,fail);
	};

	function load(dataObject,success,fail) {
		// console.log(className,'load',dataObject);
		API.get('config', dataObject, function(res) {
			console.log(className,'load get config cb',dataObject,res);
			if (success) success(res);
		},fail);
	};

	function save(newSettings,success,fail) {
		console.log(className,'save',newSettings);
		API.post('config',newSettings,success,fail);
	};
	
	function resetAll(success,fail) {
		API.post('config/resetall',{},success,fail)
	};

	function getSetting(key,success,fail) {
		console.log(className,'getSetting',key);
		API.get('config/?'+key+'=',{},function(response) {
			if (success) success(response[key]);
		},fail);
	}

	function getStartCode(success,fail) {
		loadAll(function(data) {
			var startcode = subsituteVariables(data['printer.startcode'],data);
			if (success) success(startcode);
		},fail);
	}

	function getEndCode(success,fail) {
		loadAll(function(data) {
			var endcode = subsituteVariables(data['printer.endcode'],data);
			if (success) success(endcode);
		},fail);
	}

	function subsituteVariables(gcode,settings) {
		//,temperature,bedTemperature,preheatTemperature,preheatBedTemperature
		var temperature 			      = settings["printer.temperature"];
		var bedTemperature 			    = settings["printer.bed.temperature"];
		var preheatTemperature      = settings["printer.heatup.temperature"];
		var preheatBedTemperature   = settings["printer.heatup.bed.temperature"];
	  var printerType             = settings["printer.type"];
	  var heatedbed             	= settings["printer.heatedbed"];

	  switch (printerType) {
	    case "makerbot_replicator2": printerType = "r2"; break; 
	    case "makerbot_replicator2x": printerType = "r2x"; break;
	    case "makerbot_thingomatic": printerType = "t6"; break;
	    case "makerbot_generic": printerType = "r2"; break;
	    case "_3Dison_plus": printerType = "r2"; break;
	  }
	  var heatedBedReplacement = (heatedbed)? "" : ";";

		gcode = gcode.replace(/{printingTemp}/gi  	,temperature);
		gcode = gcode.replace(/{printingBedTemp}/gi ,bedTemperature);
		gcode = gcode.replace(/{preheatTemp}/gi			,preheatTemperature);
		gcode = gcode.replace(/{preheatBedTemp}/gi 	,preheatBedTemperature);
	  gcode = gcode.replace(/{printerType}/gi     ,printerType);
	  gcode = gcode.replace(/{if heatedBed}/gi    ,heatedBedReplacement);
	    
		return gcode;
	}

	return {
		init: init,
		loadAll: loadAll,
		load: load,
		save: save,
		resetAll: resetAll,
		getSetting: getSetting,
		getStartCode: getStartCode,
		getEndCode: getEndCode,
	}
}
/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */
function InfoAPI() {
	
	this.status = function(success,fail) {
		API.get('info/status',success,fail);
	};

}
/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */
function NetworkAPI() {
	
	NetworkAPI.STATUS = {
		CONNECTING_FAILED: -1,
		NOT_CONNECTED: 0,
		CONNECTING: 1,
		CONNECTED: 2,
		CREATING: 3,
		CREATED: 4
	};
	
	var _wifiboxURL;
	var _wifiboxCGIBinURL;
	var _timeoutTime = 3000;
	
	var _self = this;

	this.init = function(wifiboxURL,wifiboxCGIBinURL) {
		//console.log("NetworkAPI:init");
		//console.log("  wifiboxURL: ",wifiboxURL);
		//console.log("  wifiboxCGIBinURL: ",wifiboxCGIBinURL);
		_wifiboxURL = wifiboxURL;
		_wifiboxCGIBinURL = wifiboxCGIBinURL;
	}
	this.scan = function(completeHandler,failedHandler) {
		//console.log("NetworkAPI:scan");
		$.ajax({
			url: _wifiboxURL + "/network/scan",
			type: "GET",
			dataType: 'json',
			timeout: _timeoutTime,
			success: function(response){
				//console.log("NetworkAPI:scan response: ",response);
				if(response.status == "error" || response.status == "fail") {
					//console.log("NetworkAPI:scan failed: ",response);
					if(failedHandler) failedHandler(response);
				} else {
					completeHandler(response.data);
				}
			}
		}).fail(function() {
			//console.log("NetworkAPI:scan failed");
			if(failedHandler) failedHandler();
		});
	};
	this.status = function(completeHandler,failedHandler) {
		//console.log("NetworkAPI:status");
		$.ajax({
			url: _wifiboxURL + "/network/status",
			type: "GET",
			dataType: 'json',
			timeout: _timeoutTime,
			success: function(response){
				//console.log("NetworkAPI:status response: ",response);
				if(response.status == "error" || response.status == "fail") {
					if(failedHandler) failedHandler(response);
				} else {
					completeHandler(response.data);
				}
			}
		}).fail(function() {
			if(failedHandler) failedHandler();
		});
	};
	
	this.associate = function(ssid,phrase,recreate) {
		//console.log("NetworkAPI:associate");
		var postData = {
				ssid:ssid,
				phrase:phrase,
				recreate:recreate
		};
		$.ajax({
			url: _wifiboxCGIBinURL + "/network/associate",
			type: "POST",
			data: postData,
			dataType: 'json',
			timeout: _timeoutTime,
			success: function(response){
				//console.log("NetworkAPI:associate response: ",response);
			}
		}).fail(function() {
			//console.log("NetworkAPI:associate: timeout (normal behavior)");
		});
	};
	
	this.openAP = function() {
		//console.log("NetworkAPI:openAP");
		$.ajax({
			url: _wifiboxCGIBinURL + "/network/openap",
			type: "POST",
			dataType: 'json',
			timeout: _timeoutTime,
			success: function(response){
				//console.log("NetworkAPI:openAP response: ",response);
			}
		}).fail(function() {
			//console.log("NetworkAPI:openAP: timeout (normal behavior)");
		});
	};
	
	this.signin = function() {
		$.ajax({
			url: _wifiboxCGIBinURL + "/network/signin",
			type: "GET",
			dataType: 'json',
			timeout: _timeoutTime,
			success: function(response){
				//console.log("NetworkAPI:signin response: ",response);
			}
		}).fail(function() {
			//console.log("NetworkAPI:signin: failed");
		});
	};
}
/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

function PrinterAPI() {
	var className = 'PrinterAPI';

	this.remainingLines = [];
	this.totalLinesAtStart = 0;

	this.init = function() {
		console.log(className,'init is deprecated');
	}

	this.state = function(success,fail) {
		API.get('printer/state',{},success,fail);
	};
	
	this.listAll = function(success,fail) {
		API.get('printer/listall',{},success,fail);
	};

	this.temperature = function(success,fail) {
		API.get('printer/temperature',{},success,fail);
	};

	this.progress = function(success,fail) {
		API.get('printer/progress',{},success,fail);
	}

	function _printPartPost(lines,data,cb) {
		
		API.post('printer/print',data,function(response) {
			console.log('print part success',response);
			setTimeout(function() {
				_printPart(lines,false,false,cb);
			},10);

		},function(jqXHR,textStatus) {
			console.log('print fail jqHXR:',jqXHR,"textStatus:",textStatus);
			if (textStatus=="timeout") {
				console.log('TIMEOUT, waiting to try again');
				setTimeout(function() {
					console.log('now try again');
					_printPartPost(lines,data,cb);
				},5000);
			} else {
				console.log("_printPartPost FATAL error:",textStatus);
			}
		});
	}

	function _printPart(lines,first,start,cb) {
		var chunk = lines.splice(0,500);
		console.log('printPart',chunk.length,lines.length);

		if (chunk.length>0) {
			var data = {gcode: chunk.join("\n"), first: first, start: start};
			
			_printPartPost(lines,data,function() {
				// console.log('_printPartPost cb');
				// cb(); //??? needed
			});

		} else {
			console.log('no more print parts');
			cb(); //finished
		}
	}

	this.print = function(gcode,start,first,success,fail) {
		//need a check here for state??
		this.remainingLines = gcode.split("\n");
		this.totalLinesAtStart = this.remainingLines.length;
		// console.log('remainingLines.length',this.remainingLines.length);
		_printPart(this.remainingLines,true,true,function() {
			console.log('done sending');
		});
	};

	this.stop = function(endcode,success,fail) {
		//need a check here for state??
		// console.log('remainingLines',this.remainingLines.length);
		this.remainingLines.length = 0; //clear array
		totalLinesAtStart = 0;
		API.post('printer/stop',{gcode:endcode},success,fail);
	}

}
/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */
 
function SketchAPI() {
  var className = 'SketchAPI';

  function load(id,success,fail) {
		API.get('sketch/?id='+id,{},success,fail);
	}

  function list(success,fail) {
    API.get('sketch/list',{},success,fail); 
  }

  function save(data,success,fail) {
    console.log(className,'saving sketch',data);
    API.post('sketch',{data:data},success,fail);
  }

  function del(id,success,fail) {
    console.log(className,'deleting sketch',id);
    API.post('sketch/delete',{id:id},success,fail);
  }

  function status(success,fail) {
     API.get('sketch/status',{},success,fail);  
  }

  return {
    load: load,
    list: list,
    save: save,
    status: status,
    del: del,
  }

}