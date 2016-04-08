/*
main.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

var debugMode = false;              // debug mode
var sendPrintCommands = true;       // if Doodle3d should send print commands to the 3d printer
var communicateWithWifibox = true;  // if Doodle3d should try interfacing with the wifibox (in case one is not connected)
var wifiboxIsRemote = false;        // when you want to run the client on a computer and have it remotely connect to the wifibox
var autoUpdate = true; 							// auto retrieve updates about temperature and progress from printer
var autoLoadSketchId;

////var printer =  new Printer();
////var progressbar = new Progressbar();
////var thermometer = new Thermometer();
////var settingsWindow = new SettingsWindow();
////var message = new Message();

var firstTimeSettingsLoaded = true;

var wifiboxURL; // Using the uhttpd lua handler as default, because of better performance
var wifiboxCGIBinURL; // CGI-bin, for some network stuff, where it needs to restart the webserver for example

var $drawAreaContainer, $doodleCanvas, doodleCanvas, doodleCanvasContext, $previewContainer;

var showhideInterval;
var showOrHide = false;
var limitedFeatures = false;

var clientInfo = {};

var POPUP_SHOW_DURATION = 175;
var BUTTON_GROUP_SHOW_DURATION = 80;

$(function() {
  console.log("ready");
  
  /*if (getURLParameter("d") != "null") debugMode = (getURLParameter("d") == "1");
  if (getURLParameter("p") != "null") sendPrintCommands = (getURLParameter("p") == "1");
  if (getURLParameter("c") != "null") communicateWithWifibox = (getURLParameter("c") == "1");
  if (getURLParameter("r") != "null") wifiboxIsRemote = (getURLParameter("r") == "1");
  if (getURLParameter("u") != "null") autoUpdate = (getURLParameter("u") == "1");
  if (getURLParameter("l") != "null") limitedFeatures = (getURLParameter("l") == "1");
  if (getURLParameter("load") != "null") autoLoadSketchId = parseInt(getURLParameter("load"));
  var hostname;
  if (wifiboxIsRemote) hostname = 'http://10.10.0.1';
  if (getURLParameter("wifiboxURL") != "null") hostname = getURLParameter("wifiboxURL");
  
  if (location.host=='doodle3d') hostname = 'http://wifibox';
  if (!hostname) hostname = "http://" + window.location.host;
  //wifiboxURL = hostname+"/myapi";
  wifiboxURL = hostname+"/";
  wifiboxCGIBinURL = hostname+"/cgi-bin/myapi";
  if (!communicateWithWifibox) {
    sendPrintCommands = false; // 'communicateWithWifibox = false' implies this
  }
  console.log("debugMode: " + debugMode);
  console.log("sendPrintCommands: " + sendPrintCommands);
  console.log("communicateWithWifibox: " + communicateWithWifibox);
  console.log("wifiboxIsRemote: " + wifiboxIsRemote);
  console.log("wifibox URL: " + wifiboxURL);
  // rudimentary client info
  clientInfo.isMobileDevice = isMobileDevice();
  clientInfo.isSmartphone = isSmartphone();
*/
  initDoodleDrawing();
  initPreviewRendering();
  initLayouting();
  // initSidebars();
  initButtonBehavior();
  ////initKeyboard();
  // initVerticalShapes();
  ////initWordArt();
  ////initShapeDialog();
  initScanDialog();

  disableDragging();
  
/*  if (!clientInfo.isSmartphone) initHelp();
	thermometer.init($("#thermometerCanvas"), $("#thermometerContainer"));
  progressbar.init($("#progressbarCanvas"), $("#progressbarCanvasContainer"));
  message.init($("#message"));
  printer.init();
	$(document).on(Printer.UPDATE,update);
	settingsWindow.init(wifiboxURL,wifiboxCGIBinURL);
	$(document).on(SettingsWindow.SETTINGS_LOADED, settingsLoaded);
	
  if(debugMode) {
    console.log("debug mode is true");
    $("body").css("overflow", "auto");
    $("#debug_textArea").css("display", "block");
    //$("#preview_tmp").css("display", "block");
    $("#debug_display").css("display", "block");
  }
  if (limitedFeatures) {
    initLimitedInterface();
  }
*/  
  
});

function disableDragging() {
  $(document).bind("dragstart", function(event) {
    console.log("dragstart");
    event.preventDefault();
  });
}

/*function showOrHideThermo() {
  console.log("f:showOrHideThermo()");
  if (showOrHide) {
    thermometer.hide();
    progressbar.hide();
  } else {
    thermometer.show();
    progressbar.show();
  }
  showOrHide = !showOrHide;
}
function settingsLoaded() {
	console.log("settingsLoaded");
	
	if(firstTimeSettingsLoaded) {
		console.log("  preheat: ",settings["printer.heatup.enabled"]);
		console.log("  state: ",state);
		if(state == Printer.IDLE_STATE && settings["printer.heatup.enabled"]) {
			printer.preheat();
		}
		console.log("doodle3d.tour.enabled: ",settings["doodle3d.tour.enabled"]);
		if(settings["doodle3d.tour.enabled"] && !clientInfo.isSmartphone) {
			console.log("show tour");
			initHelp();
		}
		firstTimeSettingsLoaded = false;
	}
	
}
function setDebugText(text) {
	$("#debug_display").text(text);
  
}*/
















/*
AddScanDialog.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */
//var shapeResolution=3;
var shapePopup;

function initScanDialog() {
  scanPopup = new Popup($("#popupScan"), $("#popupMask"));
  $("#btnScanOk").on("onButtonClick", onBtnScanOk);
  //$("#btnCloseScan").on("onButtonClick", onBtnCloseScan);
}

function onBtnCloseScan() {
  $('#imgGuide').hide();
  $('#btnCloseScan').hide();
}

function onBtnScanOk() {
  scanPopup.commit();
}

function showScanDialog() {
  scanPopup.open();
}

function readURL(input) {

    if (input.files && input.files[0]) {
        var reader = new FileReader();

        reader.onload = function (e) {
          $('#imgGuide').attr('src', e.target.result);
          $('#imgGuide').show();
          $('#btnCloseScan').show();
          scanPopup.commit();
        }

        reader.readAsDataURL(input.files[0]);
    }
}

$("#fileScan").change(function(){
    readURL(this);
});















/*
AddShapeDialog.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */
var shapeResolution=3;
var shapePopup;

function initShapeDialog() {
  shapePopup = new Popup($("#popupShape"), $("#popupMask"));
  $("#btnShapeOk").on("onButtonClick", shapePopup.commit);
  $("#btnShapeCancel").on("onButtonClick", shapePopup.cancel);
  $("#popupShape").bind("onPopupCancel", onShapeCancel);
  $("#popupShape").bind("onPopupCommit", onShapeOk);
  
  $("#btnShapePlus").on("onButtonHold",onShapePlus);
  $("#btnShapeMin").on("onButtonHold",onShapeMin);
  updateShapePreview();
}

function showShapeDialog() {
	shapePopup.open();
}

function onShapeCancel() {
}

function onShapeOk() {
  var res = shapeResolution;

  if (res!=undefined) {
    if (isNaN(res)) res=3;
    if (res<2) res=2;
    if (res>100) res=100;
    drawCircle(canvasWidth/2,canvasHeight/2,80,res);   
  }
}

function onShapePlus() {
  shapeResolution++;
  if (shapeResolution>50) shapeResolution=50;
  updateShapePreview();
}

function onShapeMin() {
  shapeResolution--;
  if (shapeResolution<2) shapeResolution=2;
  updateShapePreview();
}

function updateShapePreview() {
  $(".lblShapeResolution").text(shapeResolution + " sides");

  var canvas = $("#shapePreview")[0];
  var c = canvas.getContext('2d');
  var w = canvas.width;
  var h = canvas.height;
  //console.log(w,h);
  var r = w/2 - 20;
  var x0 = w/2;
  var y0 = h/2;
  var res = shapeResolution;
  var step = Math.PI * 2.0 / res;
  
  c.save();
  c.clearRect(0,0,canvas.width, canvas.height);
  c.restore();
  c.beginPath();
  for (var a=0; a<Math.PI*2; a+=step) {
    var x = Math.sin(a+Math.PI) * r + x0;
    var y = Math.cos(a+Math.PI) * r + y0;
    if (a==0) c.moveTo(x,y);
    else c.lineTo(x,y);
  }
  //close shape
  var x = Math.sin(0+Math.PI) * r + x0;
  var y = Math.cos(0+Math.PI) * r + y0;
  c.lineTo(x,y);

  //draw shape
  c.lineWidth = 2;
  c.stroke();
}
















/*
Button.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

// prototype inheritance 
// http://robertnyman.com/2008/10/06/javascript-inheritance-how-and-why/
Button.prototype = new jQuery();
function Button() {
	
	this.enabled = true;
	
	var _clickEnabled = true;
	var _downTimerFPS = 20;
	var _timer;
	var _x,_y;
	var _isDown = false;
	var _self = this;
		
	// call jQuery constuctor 
	// http://blog.santoshrajan.com/2008/10/what-john-resig-did-not-tell-you.html
	this.constructor.prototype.init.apply(this, arguments);
	
	// prevent multiple event handlers etc
	//	make sure you do a more general conversion last
	if(this.data("isButton")) {
		return;
	} else {
		this.data("isButton",true);
	}
	
	this.enable = function() {
		if(_self.enabled === true) { return; } 
		_self.removeClass("disabled");
		_self.enabled = true;
	};
	this.disable = function() {
		if(_self.enabled === false) { return; }
		_self.addClass("disabled");
		_self.enabled = false;
	};
	// if the element starts with a disable class, we properly disable it
	if(this.hasClass("disabled")) {
		this.disable();
	}
	
	function updateCursor(e) {
		// retrieve cursor position relative to element
		if (e.offsetX !== undefined) {
			_x = e.offsetX;
			_y = e.offsetY;
		} else {
			var offset = _self.offset();
			if(e.pageX !== undefined) {
				// http://www.quirksmode.org/mobile/tableViewport_desktop.html#t11
				_x = e.pageX - offset.left;
				_y = e.pageY - offset.top;
			} else if(e.originalEvent !== undefined && e.originalEvent.pageX !== undefined) {
				//http://css-tricks.com/the-javascript-behind-touch-friendly-sliders/
				_x = e.originalEvent.pageX - offset.left;
				_y = e.originalEvent.pageY - offset.top;
			}
		
			//android+chrome-specific hack	
			if (e.originalEvent.changedTouches !== undefined) {
				_x = e.originalEvent.changedTouches[0].pageX - offset.left;
				_y = e.originalEvent.changedTouches[0].pageY - offset.top;
			}
		}
	}
	function startDownTimer() {
		if (_timer === undefined) {
			_timer = setInterval(onDownTimerInterval, 1000/_downTimerFPS);
			_isDown = true;
		}
	}
	function stopDownTimer() {
		clearInterval(_timer);
		_timer = undefined;
		_isDown = false;
		// _x = undefined;
		// _y = undefined;
	}
	function onDownTimerInterval() {
		if(!_self.enabled) { return; }
		if (_x !== undefined && _y !== undefined) {
			_self.trigger("onButtonHold",{x:_x,y:_y});
		} else {
			console.log("Button: warning... _x or _y not set...");
		}
	}
	
	// Event handlers
	$(document).mouseup(function(e) {
		stopDownTimer();
	});
	this.on("touchstart", function(e) {
		if(!_self.enabled) { return; }
		_clickEnabled = false;
		updateCursor(e);
		startDownTimer();
		_self.trigger("onButtonClick",{x:_x,y:_y});
		e.preventDefault();
	});
	this.on("touchend", function(e) {
		updateCursor(e);
		stopDownTimer();
	});
	this.on("touchmove", function(e) {
		if(!_self.enabled) { return; }
		updateCursor(e);
		startDownTimer();
	});
	this.mousedown(function(e) {
		if(!_self.enabled) { return; }
		updateCursor(e);
		startDownTimer();
	});
	this.mouseup(function(e) {
		updateCursor(e);
		stopDownTimer();
	});
	this.mousemove(function(e) {
		if(!_self.enabled) { return; }
		updateCursor(e);
		//if (_isDown) mousedrag(e);
	});
	//this.mousedrag(function(e) {
	//	updateCursor(e);
	//});
	this.contextmenu(function(e) {
		e.preventDefault();
	});
	this.click(function(e) {
		if(!_self.enabled || !_clickEnabled) { return; }
		updateCursor(e);
		stopDownTimer();
		_self.trigger("onButtonClick",{x:_x,y:_y});
	});
}

// to work with multiple objects we need a jQuery plugin
$.fn.Button = function() {
	return $(this).each(function(){
		new Button(this);
	});
};

















/*
Message.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

function Message() {

	Message.ERROR 			= "error";
	Message.WARNING 		= "warning";
	Message.NOTICE 			= "notice";
	Message.INFO 				= "info";

	this.mode						= "";

	this.$element;

	var self = this;
	var autoHideDelay = 5000;
	var autohideTimeout;

	this.init = function($element) {
    this.$element = $element;
 	}
	this.set = function(contents,mode,autoHide,disableEffect) {
		console.log("Message:set: ",contents,mode,autoHide,disableEffect);
		if(disableEffect) {
			self.fill(contents,mode,autoHide)
		} else{
			self.hide(function() {
				self.show();
				self.fill(contents,mode,autoHide)
			});
		}
	}
	this.fill = function(contents,mode,autoHide) {
		//console.log("Message:fill: ",text,mode,autoHide);
		self.clear();
		self.$element.html(contents);
		self.$element.addClass(mode);
		self.mode = mode;
		clearTimeout(autohideTimeout);
		if(autoHide) {
			autohideTimeout = setTimeout(function(){ self.hide()},autoHideDelay);
		}
	}
	this.clear = function($element) {
		this.$element.html("");
		this.$element.removeClass(this.mode);
	}

	this.show = function() {
		this.$element.fadeIn(200);
	}
	this.hide = function(complete) {
		this.$element.fadeOut(200,complete);
	}
}

function Popup(element, mask) {
	var autoCloseEnabled = true;
	var enterEnabled = true;
	var self = this;
	
	this.open = function(complete, disableMaskClick) {
		mask.fadeIn(POPUP_SHOW_DURATION);
		element.fadeIn(POPUP_SHOW_DURATION, complete);
		
		keyboardShortcutsEnabled = false;
		keyboardEscapeEnterEnabled = true;
		
		document.body.removeEventListener('touchmove', prevent, false);
		mask.bind("onButtonClick", self.cancel);
		$(document).bind("onEscapeKey", self.cancel);
		if (enterEnabled) $(document).bind("onEnterKey", self.commit);
	}
	
	this.close = function(complete) {
		mask.fadeOut(POPUP_SHOW_DURATION);
		element.fadeOut(POPUP_SHOW_DURATION, complete);
		
		keyboardShortcutsEnabled = true;
		keyboardEscapeEnterEnabled = false;
		
		document.body.addEventListener('touchmove', prevent, false);
		mask.unbind("onButtonClick", self.cancel);
		$(document).unbind("onEscapeKey", self.cancel);
		if (enterEnabled) $(document).unbind("onEnterKey", self.commit);
	}
	
	this.setEnterEnabled = function(enabled) { enterEnabled = enabled; }
	
	this.setAutoCloseEnabled = function(enabled) { autoCloseEnabled = enabled; }
	
	this.cancel = function() {
		$(element).trigger('onPopupCancel');
		if (autoCloseEnabled) self.close();
	}
	
	this.commit = function() {
		$(element).trigger('onPopupCommit');
		if (autoCloseEnabled) self.close();
	}
}















/*
Shape.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */
 
function drawCircle(x0,y0,r,res) {
  if (res==undefined) res = 50; //circle resolution
  beginShape();
  var step = Math.PI * 2.0 / res;
  for (var a=0; a<Math.PI*2; a+=step) {
    var x = Math.sin(a+Math.PI) * r + x0;
    var y = Math.cos(a+Math.PI) * r + y0;
    if (a==0) shapeMoveTo(x,y);
    else shapeLineTo(x,y);
  }

  //close shape
  var x = Math.sin(0+Math.PI) * r + x0;
  var y = Math.cos(0+Math.PI) * r + y0;
  shapeLineTo(x,y);
  
  endShape();
}

function beginShape(x,y) {
  //setSketchModified(true);
}

function shapeMoveTo(x,y) {
  _points.push([x, y, true]);
  adjustBounds(x, y);
  adjustPreviewTransformation();
  draw(x, y, .5);
}

function shapeLineTo(x,y) {
  _points.push([x, y, false]);
  adjustBounds(x, y);
  adjustPreviewTransformation();
  draw(x, y);
}

function endShape() {
  renderToImageDataPreview();
}

function getBounds(points) {    
  var xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity;
  for (var i=0; i<points.length; i++) {
    var p = points[i];
    xMin = Math.min(xMin,p[0]);
    xMax = Math.max(xMax,p[0]);
    yMin = Math.min(yMin,p[1]);
    yMax = Math.max(yMax,p[1]);
  }
  return {x:xMin,y:yMin,width:xMax-xMin,height:yMax-yMin};
}

function translatePoints(points,x,y) {
  for (var i=0; i<points.length; i++) {
    points[i][0] += x;
    points[i][1] += y;
  }
}

function scalePoints(points,x,y) {
  if (y==undefined) y = x;
  for (var i=0; i<points.length; i++) {
    points[i][0] *= x;
    points[i][1] *= y;
  }
}

function rotatePoints(points, radians, cx, cy) {
  if (cx==undefined) cx = 0;
  if (cy==undefined) cy = 0;

  var cos = Math.cos(radians);
  var sin = Math.sin(radians);

  for (var i=0; i<points.length; i++) {
      var x = points[i][0];
      var y = points[i][1];
      var nx = (cos * (x - cx)) - (sin * (y - cy)) + cx;
      var ny = (sin * (x - cx)) + (cos * (y - cy)) + cy;
      points[i][0] = nx;
      points[i][1] = ny;
  }
}

function moveShape(x,y) {
	var bounds = getBounds(_points);
	var delta = reduceTransformToFit(x, y, 1.0, bounds);
	
	if (delta.x != 0 || delta.y != 0) {
		translatePoints(_points, delta.x, delta.y);
		updateView();
	}
}

//TODO: reduction of zoomValue is still not completely correct (but acceptable?)
//TODO: bounds should be cached and marked dirty on modification of points array; translations could be combined in several places
function zoomShape(zoomValue) {
	var bounds = getBounds(_points);
	var transform = reduceTransformToFit(0, 0, zoomValue, bounds);
	
	translatePoints(_points, transform.x, transform.y); //move points towards center as far as necessary to avoid clipping
	translatePoints(_points, -bounds.x, -bounds.y);
	translatePoints(_points, -bounds.width / 2, -bounds.height / 2);
	scalePoints(_points, transform.zf, transform.zf);
	translatePoints(_points, bounds.width / 2, bounds.height / 2);
	translatePoints(_points, bounds.x, bounds.y);
	updateView();
}

function rotateShape(radians) {
  var bounds = getBounds(_points);
  var cx = bounds.x + bounds.width/2;
  var cy = bounds.y + bounds.height/2;
  rotatePoints(_points, radians, cx, cy);
  
  var bounds = getBounds(_points);
  var transform = reduceTransformToFit(0, 0, 1.0, bounds);
  translatePoints(_points, transform.x, transform.y);
  scalePoints(_points, transform.zf, transform.zf);

  updateView();
}

function updateView() {
  //setSketchModified(true);
  redrawDoodle(true);
  adjustPreviewTransformation();
  renderToImageDataPreview();
  
  if (debugMode) {
    var bounds = getBounds(_points);
  	drawCircleTemp(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2, 5, 'red');
  }
}

//when x,y!=0,0: reduces them such that transformed bounds will still fit on canvas (given that they fit prior to the transform)
//otherwise: calculate translation + zoom reduce such that given bounds will fit on canvas after transformation
function reduceTransformToFit(x, y, zf, bounds) {
	var zw = bounds.width * zf; zh = bounds.height * zf;
	var newBounds = { x: bounds.x - (zw - bounds.width) / 2, y: bounds.y - (zh - bounds.height) / 2, width: zw, height: zh };
//	console.log("bounds: " + bounds.x + ", " + bounds.y + ", " + bounds.width + ", " + bounds.height);
//	console.log("newBounds: " + newBounds.x + ", " + newBounds.y + ", " + newBounds.width + ", " + newBounds.height);
	
	var ldx = Math.max(x, -newBounds.x);
	var rdx = Math.min(x, canvasWidth - (newBounds.x + newBounds.width));
	var tdy = Math.max(y, -newBounds.y);
	var bdy = Math.min(y, canvasHeight - (newBounds.y + newBounds.height));
	
	if (x != 0 || y != 0) { //movement was requested
		return { x: nearestZero(ldx, rdx), y: nearestZero(tdy, bdy) };
	} else { //no movement requested
		var delta = { x: ldx + rdx, y: tdy + bdy };
		if (ldx != 0 && rdx != 0) delta.x /= 2;
		if (tdy != 0 && bdy != 0) delta.y /= 2;
		
		delta.x /= zf;
		delta.y /= zf;
	
		var zxMax = Math.min(zf, canvasWidth / newBounds.width);
		var zyMax = Math.min(zf, canvasHeight / newBounds.height);
//		var oldZF = zf;
//		var dir = zf >= 1.0 ? 1 : 0;
		zf = Math.min(zxMax, zyMax);
//		if (dir == 1 && zf < 1.0) zf = 1;
//		console.log("orgZF, zxMax, zyMax, finZF: " + oldZF + ", " + zxMax + ", " + zyMax + ", " + zf);
		
		return { x: delta.x, y: delta.y, zf: zf };
	}
}

function nearestZero(v1, v2) { return Math.abs(v1) < Math.abs(v2) ? v1 : v2; }

//*draws* a circle (i.e. it is not added as points to shape)
function drawCircleTemp(x, y, r, color) {
	ctx.beginPath();
	ctx.lineWidth = 1;
	ctx.fillStyle = color;
	ctx.arc(x, y, r, 0, 2 * Math.PI, false);
	ctx.fill();
	ctx.stroke();
	ctx.fillStyle = 'black';
}















/*
WordArt.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

var wordArtPopup;

function initWordArt() {
  $("body").append('<div id="svgfont" style="display:none"></div>');
  $("#svgfont").load("/plugin/bocusini_doodler/static/img/font.svg?");
  
  wordArtPopup = new Popup($("#popupWordArt"),$("#popupMask"));
  $("#btnWordArtOk").on("onButtonClick",wordArtPopup.commit);
  $("#btnWordArtCancel").on("onButtonClick",wordArtPopup.cancel);
  $("#popupWordArt").bind("onPopupCancel", onWordArtCancel);
  $("#popupWordArt").bind("onPopupCommit", onWordArtOk);
}

function showWordArtDialog() {
  buttonGroupAdd.hide();
  wordArtPopup.open();
  $("#txtWordArt").focus();
  $("#txtWordArt").val(""); //clear textbox
}

function onWordArtCancel() {
	$("#txtWordArt").blur();
}

function onWordArtOk() {
	$("#txtWordArt").blur();
	var s = $("#txtWordArt").val();
	drawTextOnCanvas(s);
}

function drawTextOnCanvas(text) {
	if (typeof(text) == 'string') {
		var points = getStringAsPoints(text);

		var bounds = getBounds(points);
		var scaleX = (canvasWidth-50) / bounds.width;
		var scaleY = (canvasHeight-50) / bounds.height;

		var scale = Math.min(scaleX,scaleY);

		scalePoints(points,scale);
		var bounds = getBounds(points);
		translatePoints(points,-bounds.x,-bounds.y); //left top of text is (0,0)
		translatePoints(points,-bounds.width/2,-bounds.height/2); //anchor point center
		translatePoints(points,canvasWidth/2,canvasHeight/2); //center in canvas

		canvasDrawPoints(canvas,points);
	}
}

function getStringAsPoints(text) {
  var allPoints = [];
  var xPos = 0;

  for (var i=0; i<text.length; i++) {

    if (text[i]==" ") { //space
      xPos += 8;
    } else { //other characters
      var path = getPathFromChar(text[i]);
      var points = getPointsFromPath(path);

      if (points.length==0) continue;

      translatePoints(points,-points[0][0],0);

      var bounds = getBounds(points);

      translatePoints(points,-bounds.x,0);
      translatePoints(points,xPos,0);

      xPos+=bounds.width;
      xPos+=2;

      for (var j=0; j<points.length; j++) {
        allPoints.push(points[j]);
      }
    }

  }
  return allPoints;
}

function getPathFromChar(ch) {
  var index = ch.charCodeAt(0)-33;
  var element = $("#svgfont path")[index];
  if (element==undefined) return "";
  return $("#svgfont path")[index].attributes["d"].value; //was nodeValue but that's depricated
}

function getPointsFromPath(path) {
  var points = [];
  var cmds = path.split(' ');
  var cursor = { x:0.0, y:0.0 };
  var move = false;
  var prevCmd = "";
  var lastCmd = "";

  //console.log(path);

  for (var i=0; i<cmds.length; i++) {
    var cmd = cmds[i];   
    var xy = cmd.split(",");  

    if (cmd.length==1) { //we suppose this is a alpha numeric character and threat it as a command
      lastCmd = cmd;
    }

		move = (lastCmd=='m' || lastCmd=='M');

		if (xy.length==2) {
  		
      var x = parseFloat(xy[0]);
      var y = parseFloat(xy[1]);

      if (lastCmd=='m' || lastCmd=='l') { //relative movement
        cursor.x += x;
        cursor.y += y;
      } 
      else if (lastCmd=='M' || lastCmd=='L') { //absolute movement
        cursor.x = x;
        cursor.y = y;
      }

      if (lastCmd=='m') lastCmd='l'; //the next command after a relative move is relative line if not overruled
      if (lastCmd=='M') lastCmd='L'; //same for absolute moves

      points.push([cursor.x,cursor.y,move]);
    
		} else if (prevCmd == "h"){
			cursor.x += parseFloat(cmd);
			points.push([cursor.x,cursor.y,move]);
		} else if (prevCmd == "v"){
			cursor.y += parseFloat(cmd);
			points.push([cursor.x,cursor.y,move]);
		} else if (prevCmd == "H"){
			cursor.x = parseFloat(cmd);
			points.push([cursor.x,cursor.y,move]);
		} else if (prevCmd == "V"){
			cursor.y = parseFloat(cmd);
			points.push([cursor.x,cursor.y,move]);
		} 
		prevCmd = cmd;
  }
  return points;
}

function canvasDrawPoints(canvas,points) {
  beginShape();
  for (var i=0; i<points.length; i++) {
    var p = points[i];
    if (points[i][2]) shapeMoveTo(p[0],p[1]);
    else shapeLineTo(p[0],p[1]);
  }
  endShape();
}

















/*
buttonbehaviors.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

var twistIncrement = Math.PI/1800;

var btnNew, btnPrevious, btnNext, btnOops, btnStop, btnInfo;
var btnSettings, btnWordArt;
var btnToggleEdit, buttonGroupEdit, btnZoom, btnMove, btnRotate;
var btnToggleVerticalShapes, btnHeight, btnTwist, btnShape, btnConv, btnStraight, btnSine, btnDiv;
var btnFileManager, btnPDHome, btnPDX, btnPDY, btnPDZ, btnPDC, btnOctoPrint, btnShutdown;
var buttonGroupAdd, popupWordArt;
var btnScan, popupScan;

var state;
var prevState;
var hasControl;

var gcodeGenerateDelayer;
var gcodeGenerateDelay = 50;

var preheatDelay;
var preheatDelayTime = 15*1000;

var connectingHintDelay = null;
var connectingHintDelayTime = 20 * 1000;


function initButtonBehavior() {
	console.log("f:initButtonBehavior");

	btnOops = new Button("#btnOops");
	btnInfo = new Button("#btnInfo");
	btnSettings = new Button("#btnSettings");
	btnNew = new Button("#btnNew");
	btnPrint= new Button("#btnPrint");
	btnStop = new Button("#btnStop");
	btnPrevious = new Button("#btnPrevious");
	btnNext = new Button("#btnNext");
	btnSave = new Button("#btnSave");
	buttonGroupAdd = $("#buttonGroupAdd");
	btnShape = new Button("#btnShape");
	btnWordArt = new Button("#btnWordArt");
    btnScan = new Button("#btnScan");
	popupWordArt = $("#popupWordArt");
	popupShape = $("#popupShape");
    popupScan = $("#popupScan");
	popupMask = $("#popupMask");
	logoPanel = $("#logopanel");
	btnToggleEdit = new Button("#btnToggleEdit");
	buttonGroupEdit = $("#buttonGroupEdit");
	btnZoom = new Button("#btnZoom");
	btnMove = new Button("#btnMove");
	btnRotate = new Button("#btnRotate");
	btnToggleVerticalShapes = new Button("#btnToggleVerticalShapes");
	buttonGroupVerticalShapes = $("#buttonGroupVerticalShapes");
	btnHeight = new Button("#btnHeight");
	btnTwist = new Button("#btnTwist");
	btnStraight = new Button("#btnStraight");
	btnDiv = new Button("#btnDiv");
	btnConv = new Button("#btnConv");
	btnSine = new Button("#btnSine");
	btnAdd = new Button("#btnAdd");
	btnFileManager = new Button("#btnFileManager");
	btnOctoPrint = new Button("#btnOctoPrint");
	btnShutdown = new Button("#btnShutdown");
	

	//$(".btn").Button(); //initalize other buttons

	logoPanel.on("onButtonClick", onLogo);
	//btnSettings.on("onButtonClick", openSettingsWindow);
	btnSettings.on("onButtonClick", onBtnSettings);
	btnNew.on("onButtonClick", onBtnNew);
	btnAdd.on("onButtonClick", onBtnAdd);
	btnWordArt.on("onButtonClick", onBtnWordArt);
	btnShape.on("onButtonClick", onBtnShape);
    btnScan.on("onButtonClick", onBtnScan);
	btnPrint.on("onButtonClick", print);
	btnStop.on("onButtonClick", stopPrint);
	//btnSave.on("onButtonClick", saveSketch);
	//btnPrevious.on("onButtonClick", previousSketch);
	//btnNext.on("onButtonClick", nextSketch);
	btnOops.on("onButtonHold", onBtnOops);
	// vertical shape buttons
	btnToggleVerticalShapes.on("onButtonClick", onBtnToggleVerticalShapes);
	btnHeight.on("onButtonHold", onBtnHeight);
	btnTwist.on("onButtonHold", onBtnTwist);
	btnStraight.on("onButtonClick", onBtnStraight);
	btnDiv.on("onButtonClick", onBtnDiv);
	btnConv.on("onButtonClick", onBtnConv);
	btnSine.on("onButtonClick", onBtnSine);

	btnToggleEdit.on("onButtonClick", onBtnToggleEdit);
	btnMove.on("onButtonHold", onBtnMove);
	btnZoom.on("onButtonHold", onBtnZoom);
	btnRotate.on("onButtonHold", onBtnRotate);
	
	btnFileManager.on("onButtonClick", onBtnFileManager);
	//btnOctoPrint.on("onButtonClick", onBtnOctoPrint);
	btnShutdown.on("onButtonClick", onBtnShutdown);

	//getSavedSketchStatus();
	//listSketches();
	// setSketchModified(false);
	// updateSketchButtonStates();

	function onBtnToggleVerticalShapes() {
		var btnImg;
		if (buttonGroupVerticalShapes.is(":hidden")) {
			btnImg = "/plugin/bocusini_doodler/static/img/buttons/btnArrowClose.png";
		} else {
			btnImg = "/plugin/bocusini_doodler/static/img/buttons/btnArrowOpen.png";
		}
		btnToggleVerticalShapes.attr("src",btnImg);

		buttonGroupVerticalShapes.fadeToggle(BUTTON_GROUP_SHOW_DURATION);
	}

	function onLogo() {
		location.reload();
	}

	function onBtnAdd() {
		buttonGroupAdd.fadeToggle(BUTTON_GROUP_SHOW_DURATION);
	}

	function onBtnStraight() {
		setVerticalShape(verticalShapes.NONE);
	}
	function onBtnDiv() {
		setVerticalShape(verticalShapes.DIVERGING);
	}
	function onBtnConv() {
		setVerticalShape(verticalShapes.CONVERGING);
	}
	function onBtnSine() {
		setVerticalShape(verticalShapes.SINUS);
	}

	function hitTest(cursor,button,radius) {
		return distance(cursor.x,cursor.y,button.x,button.y)<radius;
	}

	function onBtnToggleEdit() {
		var btnImg;
		if(buttonGroupEdit.is(":hidden")) {
			btnImg = "/plugin/bocusini_doodler/static/img/buttons/btnArrowClose.png";
		} else {
			btnImg = "/plugin/bocusini_doodler/static/img/buttons/btnArrowOpen.png";
		}
		btnToggleEdit.attr("src",btnImg);

		buttonGroupEdit.fadeToggle(BUTTON_GROUP_SHOW_DURATION);
	}
	
	function onBtnMove(e,cursor) {
		var w = btnMove.width();
		var h = btnMove.height();
		var speedX = (cursor.x-w/2)*0.3;
		var speedY = (cursor.y-h/2)*0.3;
		//console.log("move speed: ",speedX,speedY);
		moveShape(speedX,speedY);
	}
	
	function onBtnZoom(e,cursor) {
		var h = btnZoom.height();
		var multiplier = (h/2-cursor.y)*0.003	+ 1;
		zoomShape(multiplier);
	}
	
	function onBtnRotate(e,cursor) {
		var h = btnRotate.height();
		var multiplier = (h/2-cursor.y)*0.003;
		rotateShape(-multiplier);
	}

	function onBtnHeight(e,cursor) {
		var h = btnHeight.height();
		if(cursor.y < h/2) {
			previewUp(true);
		} else {
			previewDown(true);
		}
	}
	
	function onBtnTwist(e,cursor) {
		var h = btnTwist.height();
		var multiplier = (cursor.y-h/2)*0.0005;
		previewTwist(multiplier,true);
	}

	function onBtnOops(e) {
		oopsUndo();
	}

	function onBtnNew(e) {
		newSketch();
	}

	function onBtnWordArt(e) {
		showWordArtDialog();
	}

	function onBtnShape(e) {
		showShapeDialog();
		buttonGroupAdd.fadeOut();
	}

    function onBtnScan(e) {
        showScanDialog();
		buttonGroupAdd.fadeOut();
    }
	
	function onBtnSettings(e) {
		//alert("Einstellungen");
		window.open('settings.html','settingsWindow');
		//openSettingsWindow();
	}
	
	function onBtnFileManager(e) {
		//alert("File Manager");
		location.href = "filemanager/";
	}

	function onBtnOctoPrint(e) {
		//alert("File Manager");
		window.open('http://10.10.0.1:5000','OctoPrint');
		//location.href = "http://10.10.0.1:5000";
	}
	
	function onBtnShutdown(e) {
		//alert("File Manager");
		//window.open('http://10.10.0.1:5000','OctoPrint');
		location.href = "http://10.10.0.1/cgi-bin/myapi/system/shutdown";
	}

	// 29-okt-2013 - we're not doing help for smartphones at the moment
	if (clientInfo.isSmartphone) {
		btnInfo.disable();
	} else {
		btnInfo.on("onButtonClick", function(e) {
			helpTours.startTour(helpTours.WELCOMETOUR);
		});
	}
}

function stopPrint() {
	console.log("f:stopPrint() >> sendPrintCommands = " + sendPrintCommands);
	if (sendPrintCommands) printer.stop();
	//setState(Printer.STOPPING_STATE,printer.hasControl);
	printer.overruleState(Printer.STOPPING_STATE);
}


function print(e) {
	console.log("f:print() >> sendPrintCommands = " + sendPrintCommands);

	//$(".btnPrint").css("display","none");

	if (_points.length > 2) {

		//setState(Printer.BUFFERING_STATE,printer.hasControl);
		//printer.overruleState(Printer.BUFFERING_STATE);

		btnStop.css("display","none"); // hack

		// we put the gcode generation in a little delay
		// so that for example the print button is disabled right away
		clearTimeout(gcodeGenerateDelayer);
		gcodeGenerateDelayer = setTimeout(function() {

			var gcode = generate_gcode();
			if (sendPrintCommands) {
				if(gcode.length > 0) {				
					var filename = doodler_get_filename();

					// upload generated gcode via OctoPrints File API
					var data = new FormData();
					var blob = new Blob([gcode.join("\n")], {type: "text/plain"});
					data.append("file", blob, filename);
					data.append("print", true);

					jQuery.ajax({
						url: API_BASEURL + "files/local",
						data: data,
//						print: true, // start printing after upload
						dataType: 'json',
						cache: false,
						contentType: false,
						processData: false,
						type: 'POST',
						success: doodler_gcode_upload_done,
						fail: doodler_gcode_upload_fail,
						progress: doodler_gcode_upload_progress
					});

				} else {
					printer.overruleState(Printer.IDLE_STATE);
					printer.startStatusCheckInterval();
				}
			} else {
				console.log("sendPrintCommands is false: not sending print command to 3dprinter");
			}

		}, gcodeGenerateDelay);
	} else {
		console.log("f:print >> not enough points!");
	}

	//	$.post("/doodle3d.of", { data:output }, function(data) {
	//	btnPrint.disabled = false;
	//	});
}


function clearMainView() {
	//    console.log("f:clearMainView()");
	ctx.save();
	ctx.clearRect(0,0,canvas.width, canvas.height);
	ctx.restore();
}
function resetPreview() {
	//    console.log("f:resetPreview()");

	// clear preview canvas
	previewCtx.save();
	previewCtx.clearRect(0,0,canvas.width, canvas.height);
	previewCtx.restore();

	// also make new Image, otherwise the previously cached preview can be redrawn with move up/down or twist left/right
	doodleImageCapture = new Image();

	// reset height and rotation to default values
	numLayers 	= previewDefaults.numLayers;     // current number of preview layers
	rStep 			= previewDefaults.rotation; // Math.PI/180; //Math.PI/40; //
}

function oopsUndo() {
	//    console.log("f:oopsUndo()");
	_points.pop();

	if (clientInfo.isSmartphone) {
		// do not recalc the whole preview's bounds during undo if client device is a smartphone
		redrawDoodle(false);
	} else {
		// recalc the whole preview's bounds during if client device is not a smartphone
		redrawDoodle(true);
	}
	redrawPreview();
}

function previewUp(redrawLess) {
	//    console.log("f:previewUp()");
	if (numLayers < maxNumLayers) {
		numLayers++;
	}
	//setSketchModified(true);

//	redrawPreview(redrawLess);
	redrawRenderedPreview(redrawLess);
}
function previewDown(redrawLess) {
	//    console.log("f:previewDown()");
	if (numLayers > minNumLayers) {
		numLayers--;
	}
	//setSketchModified(true);
//	redrawPreview(redrawLess);
	redrawRenderedPreview(redrawLess);
}
function previewTwistLeft(redrawLess) {
	previewTwist(-twistIncrement,true)
}
function previewTwistRight(redrawLess) {
	previewTwist(twistIncrement,true)
}
function previewTwist(increment,redrawLess) {
	console.log("previewTwist: ",increment);
	if (redrawLess == undefined) redrawLess = false;

	rStep += increment;
	if(rStep < -previewRotationLimit) rStep = -previewRotationLimit;
	else if(rStep > previewRotationLimit) rStep = previewRotationLimit;

	redrawRenderedPreview(redrawLess);
	//setSketchModified(true);
}

function resetTwist() {
	rStep = 0;
	redrawRenderedPreview();
	//setSketchModified(true);
}

function update() {
	//setState(printer.state,printer.hasControl);

	//thermometer.update(printer.temperature, printer.targetTemperature);
	//progressbar.update(printer.currentLine, printer.totalLines);
}





















/*
previewRendering.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

/* * * * * * * * * *
 *
 *  VARS
 *
 * * * * * * * * * */
var preview;
var previewCtx;

var svgPathRegExp = /[LM]\d* \d*/ig;
var svgPathParamsRegExp = /([LM])(\d*) (\d*)/;

var dragging = false;

var $canvas, canvas, ctx;
var canvasWidth, canvasHeight;

var drawCanvas;
var drawCanvasTopLeftCoords = [0, 0];

var doodleBounds = [-1, -1, -1, -1]; // left, top, right, bottom
//  var doodleScaleVals = [[0, 0], [1.0, 1.0]]; // [ [x, y], [scaleX, scaleY] ]
var doodleTransform = [0, 0, 1.0, 1.0]; // [ x, y, scaleX, scaleY ]

var _points = [];

var prevCountingTime = 0;
var movementCounter = 0;

var drawVariableLineWeight = false; // set to true to have the momentum of the mouse/touch movement result in larger/smaller strokes
var lineweight = 2;

var isModified = false;

var showTravelLines = false;

/* * * * * * * * * *
 *
 *  INIT
 *
 * * * * * * * * * */
function initDoodleDrawing() {
  //console.log("f:initDoodleDrawing()");

  $canvas = $("#mycanvas");
  canvas = $canvas[0];
  ctx = canvas.getContext('2d');

  canvasWidth = canvas.width;
  canvasHeight = canvas.height;


  //*
  //TODO make these jquery eventhandlers (works for all)
  if (!canvas.addEventListener) {
    canvas.attachEvent('onmousedown',onCanvasMouseDown);
    canvas.attachEvent('onmousemove',onCanvasMouseMove);
    canvas.attachEvent('onmouseup',onCanvasMouseUp);
    canvas.attachEvent('ontouchstart',onCanvasTouchDown);
    canvas.attachEvent('ontouchmove',onCanvasTouchMove);
    canvas.attachEvent('ontouchend',onCanvasTouchEnd);
    document.body.attachEvent('ontouchmove',prevent);
  } else {
    canvas.addEventListener('mousedown',onCanvasMouseDown,false);
    canvas.addEventListener('mousemove',onCanvasMouseMove,false);
    canvas.addEventListener('mouseup',onCanvasMouseUp,false);
    canvas.addEventListener('touchstart',onCanvasTouchDown,false);
    canvas.addEventListener('touchmove',onCanvasTouchMove,false);
    canvas.addEventListener('touchend',onCanvasTouchEnd,false);
    if (!debugMode) document.body.addEventListener('touchmove',prevent,false);
  }
  //*/

//  drawCanvas = $(".drawareacontainer");
  drawCanvas = $("#mycanvasContainer"); // $("#drawAreaContainer")

  //console.log("drawCanvasTopLeftCoords: " + drawCanvasTopLeftCoords);
//  drawCanvasTopLeftCoords[0] = drawCanvas.css("left").match(/[0-9]/g).join("");
//  drawCanvasTopLeftCoords[1] = drawCanvas.css("top").match(/[0-9]/g).join("");
  drawCanvasTopLeftCoords[0] = drawCanvas.offset().left;
  drawCanvasTopLeftCoords[1] = drawCanvas.offset().top;
//  drawCanvasTopLeftCoords[0] = drawCanvas[0].offsetParent.offsetLeft;
//  drawCanvasTopLeftCoords[1] = drawCanvas[0].offsetParent.offsetTop;

  //console.log("f:initDoodleDrawing() >> canvasWidth: " + canvasWidth);
  //console.log("f:initDoodleDrawing() >> canvasHeight: " + canvasHeight);

}

/* * * * * * * * * *
 *
 *  CANVAS DRAWING FUNCTION
 *
 * * * * * * * * * */
function draw(_x, _y, _width) {

  if (prevX == 0 && prevY ==0) {
    prevX = _x;
    prevY = _y;
  }

  ctx.beginPath();
  ctx.moveTo(prevX, prevY);

  if (showTravelLines || _width==undefined) {  //when _width=0.5 it's a travel line, when it's not supplied it's a real line.
    ctx.lineTo(_x, _y);
  } else {
    ctx.moveTo(_x, _y);
  }

  if (_width != undefined) {
    ctx.lineWidth = _width;
  } else {
    if (drawVariableLineWeight) {
      var dist = Math.sqrt(Math.pow((prevX - _x), 2) + Math.pow((prevY - _y), 2));
      if (dist < 10) {
        lineweight += .25;
      } else if (dist < 20) {
        lineweight += .5;
      } else if (dist < 30) {
        lineweight += .75;
      } else if (dist < 50) {
        lineweight += 1;
      } else if (dist < 80) {
        lineweight += 1.5;
      } else if (dist < 120) {
        lineweight += 2.25;
      } else if (dist < 170) {
        lineweight += 3.5;
      } else {
        lineweight += 2;
      }
      lineweight = Math.min(lineweight, 30);
      lineweight *= 0.90;
      lineweight = Math.max(lineweight, 1.0);
    } else {
      lineweight = 2;
    }

    ctx.lineWidth = lineweight;
  }
  ctx.lineCap = 'round';
  ctx.stroke();

  prevX = _x;
  prevY = _y;
}


/* * * * * * * * * *
 *
 *  SUPPORTING FUNCTIONS
 *
 * * * * * * * * * */
function clearDoodle() {
  //console.log("f:clearDoodle");

  //updatePrevNextButtonStateOnClear();

  _points = [];

  prevX = 0;
  prevY = 0;

  updatePrevX = -1;
  updatePrevY = -1;

  doodleBounds = [-1, -1, -1, -1]; // left, top, right, bottom
  doodleTransform = [0, 0, 1.0, 1.0]; // [ x, y, scaleX, scaleY ]

  dragging = false;

  clearMainView();
  resetPreview();
  resetVerticalShapes();

  //setSketchModified(false);
  // updateSketchButtonStates();
}

function redrawDoodle(recalcBoundsAndTransforms) {
	//console.log("canvasDrawing:redrawDoodle");
  if (recalcBoundsAndTransforms == undefined) recalcBoundsAndTransforms = false;
//  console.log("f:redrawDoodle() >> recalcBoundsAndTransforms = " + recalcBoundsAndTransforms);

  if (recalcBoundsAndTransforms == true) {
    doodleBounds = [-1, -1, -1, -1]; // left, top, right, bottom
    doodleTransform = [0, 0, 1.0, 1.0]; // [ x, y, scaleX, scaleY ]
    for (var i = 0; i < _points.length; i++) {
      adjustBounds(_points[i][0], _points[i][1]);
      adjustPreviewTransformation();
    }
  }

  clearMainView();

  prevX = 0;
  prevY = 0;

  for (var i = 0; i < _points.length; i++) {
    //      console.log("     drawing points " + _points[i]);
    if (_points[i][2] == true) {
      draw(_points[i][0], _points[i][1], 0.5);    //draw moves as thin lines
    } else {
      draw(_points[i][0], _points[i][1]);
    }
  }
}
// checks if x,y is outside doodleBounds, if so update 
 function adjustBounds(x, y) {
	 //console.log("canvasDrawing:adjustBounds");
  var newPointsOutsideOfCurrentBounds = false;
//      console.log("f:adjustBounds("+x+","+y+")");

  if (doodleBounds[0] == -1) {
    // if doodleBounds[0] is -1 then it isn't initted yet, so x and y are both the min and max vals

    doodleBounds[0] = x;
    doodleBounds[1] = y;
    doodleBounds[2] = x;
    doodleBounds[3] = y;
    return;
  }

  if (x < doodleBounds[0]) {
   doodleBounds[0] = x;
   newPointsOutsideOfCurrentBounds = true;
  }
  if (x > doodleBounds[2]) {
   doodleBounds[2] = x;
   newPointsOutsideOfCurrentBounds = true;
  }
 if (y < doodleBounds[1]) {
   doodleBounds[1] = y;
   newPointsOutsideOfCurrentBounds = true;
 }
 if (y > doodleBounds[3]) {
   doodleBounds[3] = y;
   newPointsOutsideOfCurrentBounds = true;
 }

 return newPointsOutsideOfCurrentBounds;
}

// does what exactly?
function adjustPreviewTransformation() {
	//console.log("canvasDrawing:adjustPreviewTransformation");

  doodleTransform[0] = doodleBounds[0];
  doodleTransform[1] = doodleBounds[1];

  var sclX, sclY, finalScl;
  if (_points.length < 2) {
//    console.log(_points);
    sclX = 1.0;
    sclY = 1.0;
    finalScl = Math.min(sclX, sclY);
  } else {
    sclX = canvasWidth / (doodleBounds[2] - doodleBounds[0]);
    sclY = canvasHeight / (doodleBounds[3] - doodleBounds[1]);

    // TODO  this shouldn't be a matter if choosing the smallest but should probably involve maintaining aspect ratio??
    finalScl = Math.min(sclX, sclY);
  }

  doodleTransform[2] = finalScl;
  doodleTransform[3] = finalScl;
}


/* * * * * * * * * *
 *
 *  MOUSE/TOUCH EVENTHANDLERS
 *
 * * * * * * * * * */
function onCanvasMouseDown(e) {
	//console.log("canvasDrawing:onCanvasMouseDown");
    //setSketchModified(true);

//  console.log("f:onCanvasMouseDown()");
  //  console.log("onCanvasMouseDown >> e.offsetX,e.offsetY = " + e.offsetX+","+e.offsetY);
  //  console.log("onCanvasMouseDown >> e.layerX,e.layerY= " + e.layerX+","+e.layerY);
  //  console.log("onCanvasMouseDown >> e: " , e);
  dragging = true;

  prevCountingTime = new Date().getTime();
  movementCounter = 0

  var x, y;
  if (e.offsetX != undefined) {
    x = e.offsetX;
    y = e.offsetY;
  } else {
    x = e.layerX;
    y = e.layerY;
  }
//  console.log("     x: " + x + ", y: " + y);

  _points.push([x, y, true]);
  adjustBounds(x, y);
  adjustPreviewTransformation();
  draw(x, y, 0.5);
}

var prevPoint = {x:-1, y:-1};
function onCanvasMouseMove(e) {
	//console.log("canvasDrawing:onCanvasMouseMove");
//  console.log("f:onCanvasMouseMove()");
  if (!dragging) return;

  //setSketchModified(true);

  //    console.log("onmousemove");

  var x, y;
  if (e.offsetX != undefined) {
    x = e.offsetX;
    y = e.offsetY;
  } else {
    x = e.layerX;
    y = e.layerY;
  }

  if (prevPoint.x != -1 || prevPoint.y != -1) {
    var dist = Math.sqrt(((prevPoint.x - x) * (prevPoint.x - x)) + ((prevPoint.y - y) * (prevPoint.y - y)));
    if (dist > 5) { // replace by setting: doodle3d.simplify.minDistance
      _points.push([x, y, false]);
      adjustBounds(x, y);
      adjustPreviewTransformation();
      draw(x, y);
      prevPoint.x = x;
      prevPoint.y = y;
    }
  } else {
    // this is called once, every time you start to draw a line
    _points.push([x, y, false]);
    adjustBounds(x, y);
    adjustPreviewTransformation();
    draw(x, y);
    prevPoint.x = x;
    prevPoint.y = y;
  }

  // DEBUG
//  $("#textdump").text("");
//  $("#textdump").append("doodlebounds:" + doodleBounds + "\n");
//  $("#textdump").append("doodletransform:" + doodleTransform + "\n");

  if (new Date().getTime() - prevRedrawTime > redrawInterval) {
    // redrawing the whole preview the first X points ensures that the doodleBounds is set well
    prevRedrawTime = new Date().getTime();
    // Keep fully updating the preview if device is not a smartphone.
    // (An assumption is made here that anything greater than a smartphone will have sufficient
    // performance to always redraw the preview.)
    if (_points.length < 50 || !clientInfo.isSmartphone) {
      redrawPreview();
    } else {
      updatePreview(x, y, true);
    }
  }
}
prevUpdateFullPreview = 0; // 0 is not a timeframe but refers to the _points array
prevUpdateFullPreviewInterval = 25; // refers to number of points, not a timeframe

function onCanvasMouseUp(e) {
//  console.log("f:onCanvasMouseUp()");
  //    console.log("onmouseup");
  dragging = false;
  //console.log("doodleBounds: " + doodleBounds);
  //console.log("doodleTransform: " + doodleTransform);
  //    ctx.stroke();

  //console.log("_points.length :" + _points.length);
//  console.log(_points);

  // DEBUG
//  $("#textdump").text("");
//  $("#textdump").append("doodlebounds:" + doodleBounds + "\n");
//  $("#textdump").append("doodletransform:" + doodleTransform + "\n");

//  redrawPreview();
  renderToImageDataPreview();
}

function onCanvasTouchDown(e) {
  //setSketchModified(true);

  e.preventDefault();
  //console.log("f:onCanvasTouchDown >> e: " , e);
//  var x = e.touches[0].pageX - e.touches[0].target.offsetLeft;
//  var y = e.touches[0].pageY - e.touches[0].target.offsetTop;
  var x = e.touches[0].pageX - drawCanvasTopLeftCoords[0];
  var y = e.touches[0].pageY - drawCanvasTopLeftCoords[1];
//  var x = e.touches[0].pageX;
//  var y = e.touches[0].pageY;
//  var x = e.touches[0].layerX;
//  var y = e.touches[0].layerY;

  _points.push([x, y, true]);
  adjustBounds(x, y);
  adjustPreviewTransformation();
  draw(x, y, .5);

  movementCounter = 0;

  prevRedrawTime = new Date().getTime();
}

function onCanvasTouchMove(e) {
	//console.log("canvasDrawing:onCanvasTouchMove");
  //setSketchModified(true);

  e.preventDefault();
//  var x = e.touches[0].pageX - e.touches[0].target.offsetLeft;
//  var y = e.touches[0].pageY - e.touches[0].target.offsetTop;
    var x = e.touches[0].pageX - drawCanvasTopLeftCoords[0];
    var y = e.touches[0].pageY - drawCanvasTopLeftCoords[1];
//    var x = e.touches[0].layerX;
//    var y = e.touches[0].layerY;
//  var x = e.touches[0].layerX;
//  var y = e.touches[0].layerY;

  //console.log("f:onCanvasTouchMove >> x,y = "+x+","+y+" , e: " , e);

  if (prevPoint.x != -1 || prevPoint.y != -1) {
    var dist = Math.sqrt(Math.pow((prevPoint.x - x), 2) + Math.pow((prevPoint.y - y), 2));
    if (dist > 5) {
      _points.push([x, y, false]);
      adjustBounds(x, y)
      adjustPreviewTransformation();
      draw(x, y);
      prevPoint.x = x;
      prevPoint.y = y;
    }
  } else {
    _points.push([x, y, false]);
    adjustBounds(x, y)
    adjustPreviewTransformation();
    draw(x, y);
    prevPoint.x = x;
    prevPoint.y = y;
  }

  // update counter -> this was for getting a handle on how often the Canvas fires a move-event
  /*
   movementCounter++;
   if (new Date().getTime() - prevCountingTime > 1000) {
   //      console.log("number of moves in 1sec: " + movementCounter)
   prevCountingTime= new Date().getTime();
   $("#numtimes").text(movementCounter + " times");
   movementCounter = 0;
   }
   //*/

  if (new Date().getTime() - prevRedrawTime > redrawInterval) {
    // redrawing the whole preview the first X points ensures that the doodleBounds is set well
    if (_points.length < 50) {
      redrawPreview();
    } else {
      updatePreview(x, y, true);
      /*
      if (_points.length - prevUpdateFullPreview > prevUpdateFullPreviewInterval) {
        console.log("f:onTouchMove >> passed prevUpdateFullPreviewInterval, updating full preview");
        redrawPreview();
        prevUpdateFullPreview = _points.length;
      } else {
        updatePreview(x, y, true);
      }
      //*/
    }
    prevRedrawTime = new Date().getTime();
  }
}

function onCanvasTouchEnd(e) {
  //console.log("f:onCanvasTouchEnd()");
  //console.log("doodleBounds: " + doodleBounds);
  //console.log("doodleTransform: " + doodleTransform);
  //    ctx.stroke();

  //console.log("_points.length :" + _points.length);

  //  redrawPreview();
  renderToImageDataPreview();
}

function prevent(e) {
  e.preventDefault();
}














/*
gcodeGenerating.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

var MAX_POINTS_TO_PRINT = 200000
var gcode = [];

function generate_gcode() {
  console.log("f:generategcode()");

  gcode = [];

  // settings are declared in print_settings.js
  var speed 						      = settings["printer.speed"];
  var normalSpeed 			      = speed;
  var bottomSpeed 			      = settings["printer.bottomLayerSpeed"];
  var firstLayerSlow			  = settings["printer.firstLayerSlow"];
  var bottomFlowRate			  = settings["printer.bottomFlowRate"];
  var travelSpeed 			      = settings["printer.travelSpeed"]
  var filamentThickness       = settings["printer.filamentThickness"];
  var wallThickness 		      = settings["printer.wallThickness"];
  var screenToMillimeterScale = settings["printer.screenToMillimeterScale"];
  var layerHeight 			      = settings["printer.layerHeight"];
  var temperature 			      = settings["printer.temperature"];
  var bedTemperature 			    = settings["printer.bed.temperature"];
  var useSubLayers 			      = settings["printer.useSubLayers"];
  var enableTraveling 	      = settings["printer.enableTraveling"];
  var retractionEnabled 	    = settings["printer.retraction.enabled"];
  var retractionspeed 	      = settings["printer.retraction.speed"];
  var retractionminDistance   = settings["printer.retraction.minDistance"];
  var retractionamount 	      = settings["printer.retraction.amount"];
  var preheatTemperature      = settings["printer.heatup.temperature"];
  var preheatBedTemperature   = settings["printer.heatup.bed.temperature"];
  var printerDimensionsX   		= settings["printer.dimensions.x"];
  var printerDimensionsY      = settings["printer.dimensions.y"];
  var printerDimensionsZ      = settings["printer.dimensions.z"];

  var gCodeOffsetX = printerDimensionsX/2;
  var gCodeOffsetY = printerDimensionsY/2;

  var startCode = generateStartCode();
  var endCode = generateEndCode();

  // max amount of real world layers
  var layers = printerDimensionsZ / layerHeight; //maxObjectHeight instead of objectHeight

  // translate numLayers in preview to objectHeight in real world
  objectHeight = Math.round(numLayers/maxNumLayers*printerDimensionsZ);

  // translate preview rotation (per layer) to real world rotation
  var rStepGCode = rStep * maxNumLayers/layers; ///maxNumLayers*maxObjectHeight;
  
  // correct direction
  rStepGCode = -rStepGCode;

  // copy array without reference -> http://stackoverflow.com/questions/9885821/copying-of-an-array-of-objects-to-another-array-without-object-reference-in-java
  var points = JSON.parse(JSON.stringify(_points));

  // add gcode begin commands
  gcode = gcode.concat(startCode);

  var layers = printerDimensionsZ / layerHeight; //maxObjectHeight instead of objectHeight
  var extruder = 0.0;
  var prev = new Point(); prev.set(0, 0);

  // replacement (and improvement) for ofxGetCenterofMass
  var centerOfDoodle = {
    x: doodleBounds[0] + (doodleBounds[2]- doodleBounds[0])/2,
    y: doodleBounds[1] + (doodleBounds[3] - doodleBounds[1])/2
  }

  console.log("f:generategcode() >> layers: " + layers);
  if (layers == Infinity) return;

	// check feasibility of design
	var pointsToPrint = points.length * layers*(objectHeight/printerDimensionsZ)

	console.log("pointsToPrint: ",pointsToPrint);

  if(pointsToPrint > MAX_POINTS_TO_PRINT) {
  	alert("Sorry, your doodle is too complex or too high. Please try to simplify it.");
  	console.log("ERROR: to many points too convert to gcode");
  	return [];
  }

  for (var layer = 0; layer < layers; layer++) {

    //gcode.push(";LAYER:"+layer); //this will be added in a next release to support GCODE previewing in CURA

    var p = JSON.parse(JSON.stringify(points)); // [].concat(points);

    if (p.length < 2) return;
    var even = (layer % 2 == 0);
    var progress = layer / layers;

    var layerScale = scaleFunction(progress);

    // if begin point this row and end point last row are close enough, isLoop is true
    var isLoop = lineLength(points[0][0], points[0][1], points[points.length-1][0], points[points.length-1][1]) < 3;

    // set center of doodle as middle (ie subtract to that)
    pointsTranslate(p, -centerOfDoodle.x, -centerOfDoodle.y);
    pointsScale(p, screenToMillimeterScale,-screenToMillimeterScale);
    pointsScale(p, layerScale, layerScale);
    pointsRotate(p, rStepGCode * layer);

    if (layer == 0) {
      //gcode.push("M107"); //fan off
      if (firstLayerSlow) {
	      //gcode.push("M220 S20"); //slow speed
	      speed = bottomSpeed;
			  //console.log("> speed: ",speed);
      }
    } else if (layer == 2) { ////////LET OP, pas bij layer 2 weer op normale snelheid ipv layer 1
      gcode.push("M106");      //fan on
      //gcode.push("M220 S100"); //normal speed
      speed = normalSpeed;
  	  //console.log("> speed: ",speed);
    }

    var curLayerCommand = 0;
    var totalLayerCommands = p.length;
    var layerProgress = 0;

    var paths = [];
    var pathCounter = -1;
    //  var points = [];

    for (var i = 0; i < p.length; i++) {
      if (p[i][2] == true) {
        pathCounter++;
        paths.push([]);
        paths[pathCounter].push([p[i][0], p[i][1]]);
      } else {
        paths[pathCounter].push([p[i][0], p[i][1]]);
      }
    }

    // loop over the subpaths (the separately drawn lines)
    for (var j = 0; j < paths.length; j++) { // TODO paths > subpaths
      var commands = paths[j];

      // loop over the coordinates of the subpath
      for (var i = 0; i < commands.length; i++) {
        var last = commands.length - 1;

        var to = new Point(); to.set(commands[i][0], commands[i][1]);

        to.x += gCodeOffsetX;
        to.y += gCodeOffsetY;

        var sublayer = (layer == 0) ? 0.0 : layer + (useSubLayers ? (curLayerCommand/totalLayerCommands) : 0);
        var z = (sublayer + 1) * layerHeight; // 2013-09-06 removed zOffset (seemed to be useless)

        var isTraveling = !isLoop && i==0;
        var doRetract = retractionEnabled && prev.distance(to) > retractionminDistance;


//if (firstPointEver || layer > 2 && enableTraveling && isTraveling) { //always travel to first point, then disable traveling for first two layers and use settings for remainder of print

        var firstPointEver = (layer == 0 && i == 0 && j == 0);
        if (enableTraveling && isTraveling) { //always travel to first point, then disable traveling for first two layers and use settings for remainder of print
          if (!firstPointEver && doRetract) gcode.push("G0 E" + (extruder - retractionamount).toFixed(3) + " F" + (retractionspeed * 60).toFixed(3)); //retract
          gcode.push("G0 X" + to.x.toFixed(3) + " Y" + to.y.toFixed(3) + " Z" + z.toFixed(3) + " F" + (travelSpeed * 60).toFixed(3));
          if (!firstPointEver && doRetract) gcode.push("G0 E" + extruder.toFixed(3) + " F" + (retractionspeed * 60).toFixed(3)); // return to normal
        } else {
          var f = (layer < 2) ? bottomFlowRate : 1;
          extruder += prev.distance(to) * wallThickness * layerHeight / (Math.pow((filamentThickness/2), 2) * Math.PI) * f;
          gcode.push("G1 X" + to.x.toFixed(3) + " Y" + to.y.toFixed(3) + " Z" + z.toFixed(3) + " F" + (speed * 60).toFixed(3) + " E" + extruder.toFixed(3));
        }

        curLayerCommand++;
        layerProgress = curLayerCommand/totalLayerCommands;
        prev = to;

      }

    }

    if ((layer/layers) > (objectHeight/printerDimensionsZ)) {
      console.log("f:generategcode() >> (layer/layers) > (objectHeight/printerDimensionsZ) is true -> breaking at layer " + (layer + 1));
      break;
    }
  }
  // add gcode end commands
  gcode = gcode.concat(endCode);

  return gcode;
}

function generateStartCode() {
	var printerType = settings["printer.type"];
	var startCode = settings["printer.startcode"];
	startCode = subsituteVariables(startCode);
	startCode = startCode.split("\n");
	return startCode;
}
function generateEndCode() {
	var printerType = settings["printer.type"];
	var endCode = settings["printer.endcode"];
	endCode = subsituteVariables(endCode);
	endCode = endCode.split("\n");
	return endCode;
}

function subsituteVariables(gcode) {
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

function scaleFunction(percent) {
  var r = 1.0;

  switch (VERTICALSHAPE) {
    case verticalShapes.NONE:
      r = 1.0;
      break;
    case verticalShapes.DIVERGING:
      r = .5 + (percent * .5);
      break;
    case verticalShapes.CONVERGING:
      r = 1.0 - (percent * .8);
      break;
    case verticalShapes.SINUS:
      r = (Math.cos(percent * Math.PI * 4) * .25) + .75;
      break;
  }

//  return 1.0 - (percent *.8);
  return r;
}

pointsTranslate = function(p, x, y) {
  for (var i = 0; i < p.length; i++) {
    p[i][0] += x;
    p[i][1] += y;
  }
}

pointsScale = function(p, sx, sy) {
  for (var i = 0; i < p.length; i++) {
    p[i][0] *= sx;
    p[i][1] *= sy;
  }
}

// rotates around point 0,0 (origin).
// Not the prettiest kind of rotation solution but in our case we're assuming that the points have just been translated to origin
pointsRotate = function(p, ang) {
  var _ang, dist;
  for (var i = 0; i < p.length; i++) {
    dist = Math.sqrt(p[i][0] * p[i][0] + p[i][1] * p[i][1]);
    _ang = Math.atan2(p[i][1], p[i][0]);
    p[i][0] = Math.cos(_ang + ang) * dist;
    p[i][1] = Math.sin(_ang + ang) * dist;
  }
}

//+ Jonas Raoni Soares Silva
//@ http://jsfromhell.com/math/line-length [rev. #1]
lineLength = function(x, y, x0, y0){
  return Math.sqrt((x -= x0) * x + (y -= y0) * y);
};

var Point = function() {};
Point.prototype = {
  x: 0,
  y: 0,
  set: function(_x, _y) {
    this.x = _x;
    this.y = _y;
  },
  distance: function(p) {
    var d = -1;
    if (p instanceof Point) {
      d = Math.sqrt((p.x - this.x) * (p.x - this.x) + (p.y - this.y) * (p.y - this.y));
    }
    return d;
  },
  toString: function() {
    console.log("x:" + this.x + ", y:" + this.y);
  }
}















/*
init_layout.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

// TODO refactor this stuff, there's much to wipe
var drawAreaContainerMinHeight = 300;
var drawAreaContainerMaxHeight = 450;

function doOnResize() {
  //    console.log("doOnResize() >> " + new Date().getTime());
  canvas.width = $canvas.width();
  canvas.height = $canvas.height(); // canvas.clientHeight;

  preview.width = $preview.width();
  preview.height = $drawAreaContainer.height();

  canvasWidth = canvas.width;
  canvasHeight = canvas.height;

//  console.log("   preview.width: " + preview.width + ", $preview.width(): " + $preview.width());

  calcPreviewCanvasProperties();

  drawCanvasTopLeftCoords[0] = drawCanvas.offset().left;
  drawCanvasTopLeftCoords[1] = drawCanvas.offset().top;

  redrawDoodle();
  redrawPreview();
}

function initLayouting() {
  //console.log("f:initLayouting()");

  $drawAreaContainer = $("#drawareacontainer");

  canvas.width = $canvas.width();
  canvas.height = $canvas.height(); // canvas.clientHeight;

  preview.width = $preview.width();
  preview.height = $drawAreaContainer.height();

  canvasWidth = canvas.width;
  canvasHeight = canvas.height;

  $drawAreaContainer.show();

  // window.innerHeight
  //console.log("window.innerHeight: " + window.innerHeight);
  //console.log("window.innerWidth: " + window.innerWidth);
  //console.log("$drawAreaContainer.innerHeight(): " + $drawAreaContainer.innerHeight());
  //console.log("$drawAreaContainer.offset().top: " + $drawAreaContainer.offset().top);

  // timeout because it SEEMS to be beneficial for initting the layout
  // 2013-09-18 seems beneficial since when?
  setTimeout(_startOrientationAndChangeEventListening, 1000);
}

function _startOrientationAndChangeEventListening() {
  // Initial execution if needed

  $(window).on('resize', doOnResize);

  // is it necessary to call these? Aren't they called by the above eventhandlers?
  doOnResize();
}


/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

//*
var $preview;
var preview;
var previewCtx;

var preview_tmp;
var previewCtx_tmp;

var previewDefaults = {
	rotation: 0, //Math.PI/90,
	numLayers: 4, //was 1
	showTravelLines: false
}

var svgPathRegExp = /[LM]\d* \d*/ig;
var svgPathParamsRegExp = /([LM])(\d*) (\d*)/;

var prevRedrawTime = new Date().getTime();
var redrawInterval = 1000 / 30; // ms

function initPreviewRendering() {
  //console.log("f:initPreviewRendering()");

  $preview = $("#preview");
  preview = $preview[0];
  previewCtx = preview.getContext('2d');

  // DEBUG --> mbt preview_tmp (voor de toImageData truc)
  var _ratio  = preview.width / canvas.width;
  preview_tmp = document.getElementById('preview_tmp');
  preview_tmp.width = preview.width;
  preview_tmp.height = canvas.height * _ratio;
  $("#preview_tmp").css("top", -preview_tmp.height);

  previewCtx_tmp = preview_tmp.getContext('2d');

//  doodleImageCapture = new Image();

  calcPreviewCanvasProperties();
  redrawPreview();

  // needed to
//  doodleImageCapture = new Image();
}

function calcPreviewCanvasProperties() {
//  console.log("f:calcPreviewCanvasProperties()");

  globalScale = preview.width / canvasWidth;
  layerCX			= (canvasWidth / 2) * globalScale;  // defined in canvasDrawing_v01.js
  layerCY			= (canvasHeight / 2) * globalScale; // defined in canvasDrawing_v01.js
//  layerOffsetY = preview.height - 1.75 * layerCY;
  layerOffsetY = preview.height * (1 - previewVerticalPadding.bottom);
  yStep 			= (preview.height - (preview.height * (previewVerticalPadding.top + previewVerticalPadding.bottom))) / maxNumLayers;
}

// TODO (perhaps) : make the twist limit dynamic, depending on what's printable (w.r.t. overlapping)
var previewRotationLimit = Math.PI / 30; // rough estimate

var numLayers 	= previewDefaults.numLayers;     // current number of preview layers
var maxNumLayers= 100;    // maximum number of preview layers
var minNumLayers= 2;      // minimum number of preview layers
var globalScale = 0.3;		// global scale of preview (width preview / width canvas)
var globalAlpha = 0.20;   // global alpha of preview
var scaleY 			= 0.4; 		// additional vertical scale per path for 3d effect
var viewerScale = 0.65;   // additional scale to fit into preview nicely (otherwise is fills out totally)
var previewVerticalPadding = { "top" : .15, "bottom" : 0.12 }; // %
var strokeWidth = 2;      //4;
//var rStep 			= Math.PI/40; //Math.PI/40; //
var rStep 			= previewDefaults.rotation; // Math.PI/180; //Math.PI/40; //
var yStep;// 			= preview.height / 150; // 3; //6;
//var svgWidth 		= 500; // 650 //parseInt($(svg).css("width"));
//var svgHeight 	= 450; //450; //parseInt($(svg).css("height"));
var layerCX, layerCY;
//var layerCX			= (canvasWidth / 2) * globalScale;  // defined in canvasDrawing_v01.js
//var layerCY			= (canvasHeight / 2) * globalScale; // defined in canvasDrawing_v01.js
var layerOffsetY; //= preview.height - 1.75 * layerCY; // 330; // previewHeight - 120
var prevX 			= 0;
var prevY 			= 0;
var highlight		= true; //highlight bottom, middle and top layers

var linesRaw = "";
var debug_redrawSimplification = 6;
function redrawPreview(redrawLess) {
	//console.log("PreviewRendering:redrawPreview");
  if (redrawLess == undefined) redrawLess = false;

  if (_points.length < 2) {
	  previewCtx.clearRect(0, 0, preview.width, preview.height);
	  return;
  }

  if (!redrawLess) {
    //debug_redrawSimplification = Math.round(_points.length / 65);
    //*
    if (_points.length < 100) {
      debug_redrawSimplification = 6;
    } else if (_points.length < 250) {
      debug_redrawSimplification = 7;
    } else if (_points.length < 400) {
      debug_redrawSimplification = 8;
    } else if (_points.length < 550) {
      debug_redrawSimplification = 9;
    } else if (_points.length < 700) {
      debug_redrawSimplification = 10;
    } else {
      debug_redrawSimplification = 11;
    }
    //*/
//    console.log("debug_redrawSimplification: " + debug_redrawSimplification);
  }

  var y = 0;
  var r = 0;

  //preview.width = preview.width;
  previewCtx.clearRect(0, 0, preview.width, preview.height);
  previewCtx.lineWidth = strokeWidth;
  previewCtx.strokeStyle = '#f00'; //"rgba(255,255,0,0)";

  for(var i = 0; i < numLayers; i++) {

    var verticalScaleFactor = scaleFunction(i / maxNumLayers);

    if(i == 0 || i == Math.floor(numLayers/2) || i == numLayers-1) {
      previewCtx.globalAlpha = 1;
    } else {
      previewCtx.globalAlpha = globalAlpha;
    }

    if (redrawLess && i%debug_redrawSimplification != 0 && !(i == 0 || i == Math.floor(numLayers/2) || i == numLayers-1) ) {
      y -= yStep;
      r += rStep;
      continue;
    }

    previewCtx.save();

//    previewCtx.translate(layerCX, layerOffsetY + layerCY + y);
    previewCtx.translate(layerCX, layerOffsetY + y);
//    previewCtx.setTransform(1, 0, 0, scaleY, layerCX, layerOffsetY+layerCY+y);
    previewCtx.scale(viewerScale * verticalScaleFactor, scaleY * viewerScale * verticalScaleFactor);
    previewCtx.rotate(r);
    previewCtx.translate((-doodleTransform[0]) * (globalScale * doodleTransform[2]), (-doodleTransform[1]) * (globalScale * doodleTransform[3]));

    var adjustedDoodlePoint = centeredAndScaledDoodlePoint(_points[0]);

    previewCtx.beginPath();
    previewCtx.moveTo(adjustedDoodlePoint.x, adjustedDoodlePoint.y);
    for(var j = 1; j < _points.length; j++) {
      adjustedDoodlePoint = centeredAndScaledDoodlePoint(_points[j])
      if (redrawLess && j%debug_redrawSimplification != 0 ) continue;
      previewCtx.lineTo(adjustedDoodlePoint.x, adjustedDoodlePoint.y);
    }
    previewCtx.stroke();

    y -= yStep;
    r += rStep;
    previewCtx.restore();
  }
  previewCtx.globalAlpha = globalAlpha;
}

function renderToImageDataPreview() {
	//console.log("PreviewRendering:renderToImageDataPreview");
  if (_points.length < 2) return;

  //*
  // the first step
  previewCtx_tmp.clearRect(0, 0, preview.width, preview.height);
  previewCtx_tmp.lineWidth = strokeWidth;
  previewCtx_tmp.strokeStyle = '#f00'; //"rgba(255,255,0,0)";

  previewCtx_tmp.save();
  previewCtx_tmp.translate(layerCX, layerCY);
  previewCtx_tmp.scale(viewerScale, viewerScale);
  previewCtx_tmp.translate((-doodleTransform[0]) * (globalScale * doodleTransform[2]), (-doodleTransform[1]) * (globalScale * doodleTransform[3]));

  var adjustedDoodlePt = centeredAndScaledDoodlePoint(_points[0]);

  previewCtx_tmp.beginPath();
  previewCtx_tmp.moveTo(adjustedDoodlePt.x, adjustedDoodlePt.y);
  for(var j = 1; j < _points.length; j++) {
    adjustedDoodlePt = centeredAndScaledDoodlePoint(_points[j])
    
    if (!previewDefaults.showTravelLines && _points[j][2]==true) {
      previewCtx_tmp.moveTo(adjustedDoodlePt.x, adjustedDoodlePt.y);
    } else {
      previewCtx_tmp.lineTo(adjustedDoodlePt.x, adjustedDoodlePt.y);
    }
  }
  previewCtx_tmp.stroke();
  previewCtx_tmp.closePath();
  previewCtx_tmp.restore();
  //*/

  //  var saved_rect = previewCtx_tmp.getImageData(0, 0, layerCX*2, layerCY*2);
  var saved_rect_todataurl = preview_tmp.toDataURL();
  doodleImageCapture = new Image();
  doodleImageCapture.onload = function() {

    previewCtx.clearRect(0, 0, preview.width, preview.height);
    previewCtx.lineWidth = strokeWidth;
    previewCtx.strokeStyle = '#f00'; //"rgba(255,255,0,0)";

    var y = 0;
    var r = 0;

    for(var i=0;i<numLayers;i++) {

      var verticalScaleFactor = scaleFunction(i / maxNumLayers);

      if(i == 0 || i == Math.floor(numLayers/2) || i == numLayers-1){
        previewCtx.globalAlpha = 1;
      } else {
        previewCtx.globalAlpha = globalAlpha;
      }

      previewCtx.save();

      previewCtx.translate(layerCX,layerOffsetY+y);
//      previewCtx.scale(1, scaleY)
      previewCtx.scale(verticalScaleFactor, scaleY * verticalScaleFactor)
      previewCtx.rotate(r);
      previewCtx.translate(-layerCX,-layerCY);

      previewCtx.drawImage(doodleImageCapture, 0, 0);

      y -= yStep;
      r += rStep;
      previewCtx.restore();
    }
  };
  doodleImageCapture.src = saved_rect_todataurl;

  previewCtx.globalAlpha = globalAlpha;
}

// called by the move up/down, twist left/right or new buttons
// it is assumed that the preview has been rendered to an Image object, which will be used to draw the preview with (much better performance)
function redrawRenderedPreview(redrawLess) {
	//console.log("PreviewRendering:redrawRenderedPreview");
  if (redrawLess == undefined) redrawLess = false;
//  console.log("f:redrawRenderedPreview()");

  previewCtx.clearRect(0, 0, preview.width, preview.height);
  previewCtx.lineWidth = strokeWidth;
  previewCtx.strokeStyle = '#f00'; //"rgba(255,255,0,0)";

  var y = 0;
  var r = 0;
  
  // check if there is preview image data that we can use for the layers
  if(!doodleImageCapture.src || doodleImageCapture.src == "") return;
  
  for(var i = 0; i < numLayers; i++) {

    var verticalScaleFactor = scaleFunction(i / maxNumLayers);

    if(i == 0 || i == Math.floor(numLayers/2) || i == numLayers-1){
      previewCtx.globalAlpha = 1;
    } else {
      previewCtx.globalAlpha = globalAlpha;
    }

    if (redrawLess && i%2 != 0 && !(i == 0 || i == Math.floor(numLayers/2) || i == numLayers-1) ) {
      y -= yStep;
      r += rStep;
      continue;
    }
    previewCtx.save();

    previewCtx.translate(layerCX,layerOffsetY+y);
//    previewCtx.scale(1, scaleY)
    previewCtx.scale(verticalScaleFactor, scaleY * verticalScaleFactor);
    previewCtx.rotate(r);
    previewCtx.translate(-layerCX,-layerCY);
    
    previewCtx.drawImage(doodleImageCapture, 0, 0);

    y -= yStep;
    r += rStep;
    previewCtx.restore();
  }
}

function centeredAndScaledDoodlePoint(p) {
  var obj = { x: 0, y: 0};

  obj.x = (p[0] - ((doodleBounds[2] - doodleBounds[0])/2)) * (globalScale * doodleTransform[2]);
  obj.y = (p[1] - ((doodleBounds[3] - doodleBounds[1])/2)) * (globalScale * doodleTransform[3]);
//  obj.x = (p[0] - (doodleBounds[2] - doodleBounds[0])) * (globalScale * doodleTransform[2]);
//  obj.y = (p[1] - (doodleBounds[3] - doodleBounds[1])) * (globalScale * doodleTransform[3]);
//  obj.x = (p[0] - doodleTransform[0]) * (globalScale * doodleTransform[2]);
//  obj.y = (p[1] - doodleTransform[1]) * (globalScale * doodleTransform[3]);

  return obj;
}

//*
var updatePrevX = -1;
var updatePrevY = -1;
function updatePreview(_x, _y, redrawLess) {
  
	//console.log("PreviewRendering:updatePreview");
  if (redrawLess == undefined) redrawLess = false;
  redrawLess = false;

  if (_points.length < 2) return;
  if (updatePrevX == -1 || updatePrevY == -1) {
    updatePrevX = _x;
    updatePrevY = _y;
    return;
  }

//  if (_points.length < 16 && Math.sqrt(Math.pow((updatePrevX - _x), 2) + Math.pow((updatePrevY - _y), 2)) < 8) return;

  var y = 0;
  var r = 0;

  previewCtx.lineWidth = strokeWidth;
  previewCtx.strokeStyle = '#f00'; //"rgba(255,255,0,0)";

  for(var i = 0; i < numLayers; i++) {

    if(i == 0 || i == Math.floor(numLayers/2) || i == numLayers-1) {
      previewCtx.globalAlpha = 1;
    } else {
      previewCtx.globalAlpha = globalAlpha;
    }

    if (redrawLess && i%debug_redrawSimplification != 0 && !(i == 0 || i == Math.floor(numLayers/2) || i == numLayers-1) ) {
      y -= yStep;
      r += rStep;
      continue;
    }

    previewCtx.save();

//    previewCtx.translate(layerCX, layerOffsetY + layerCY + y);
    previewCtx.translate(layerCX, layerOffsetY + y);
    previewCtx.scale(viewerScale, scaleY * viewerScale);
    previewCtx.rotate(r);
    previewCtx.translate((-doodleTransform[0]) * (globalScale * doodleTransform[2]), (-doodleTransform[1]) * (globalScale * doodleTransform[3]));


    previewCtx.beginPath();
    var prevPoint = centeredAndScaledDoodlePoint([updatePrevX, updatePrevY]);
    previewCtx.moveTo(prevPoint.x, prevPoint.y);
    var adjustedDoodlePoint = centeredAndScaledDoodlePoint([_x, _y]);
    previewCtx.lineTo(adjustedDoodlePoint.x, adjustedDoodlePoint.y);
    previewCtx.stroke();

    y -= yStep;
    r += rStep;
    previewCtx.restore();
  }
  previewCtx.globalAlpha = globalAlpha;
  updatePrevX = _x;
  updatePrevY = _y;

}














/*
sketches.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
*/
function newSketch(e) {
	clearDoodle();
	curSketch = sketches.length; //index of the last item + 1
	//updateSketchButtonStates();
}














/*
utils.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

// http://stackoverflow.com/questions/1403888/get-url-parameter-with-jquery
// returns true for smartphones (Android will be a bit dodgy (tablet or phone, all depends on pixels vs devicePixelRatio...)
function isSmartphone() {
  var returnBool = false;
  if( /Android/i.test(navigator.userAgent) && window.devicePixelRatio > 1) {
    var w = $(window).width() / window.devicePixelRatio;
    console.log("Android device >> ratio'd width: " + w);
    if (w < 480) {
      returnBool = true;
    }
  } else {
    returnBool = /Android|webOS|iPhone|iPod|BlackBerry|IEMobile|Opera Mini|Windows Mobile/i.test(navigator.userAgent)
  }

  return returnBool;
}

function distance(x1, y1, x2, y2) {
	return Math.sqrt((x2-x1)*(x2-x1)+(y2-y1)*(y2-y1));
}















/*
verticalShapes.js
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

var VERTICALSHAPE;

var verticalShapes = {
  "NONE": 'none',
  "DIVERGING": 'diverging',
  "CONVERGING": 'converging',
  "SINUS": 'sinus'
};

function setVerticalShape(s) {
	VERTICALSHAPE = s;
  redrawRenderedPreview();
}

function initVerticalShapes() {
  resetVerticalShapes();
}

function resetVerticalShapes() {
  setVerticalShape(verticalShapes.NONE);
}


