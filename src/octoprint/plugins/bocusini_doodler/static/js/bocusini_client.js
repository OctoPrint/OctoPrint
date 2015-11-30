/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

function FormPanel() {
	var className = 'FormPanel';
	
	var _configAPI = new ConfigAPI();
	var _retryDelay = 2000;
	var _retrySaveSettingsDelay;
	var _retryLoadAllSettingsDelay;
	var _retryLoadSettingsDelay;
	var _retryResetSettingsDelay;
	
	// ui elements
	var _element;
	
	var _self = this;
	
	this.init = function(wifiboxURL,wifiboxCGIBinURL,panelElement) {
		
		// make _self the scope of which init was called?
		// needed to have the subclass instance access the same counter 
		//_self = this; 
		//console.log("  _element: ",_element);
		_element = panelElement;
		//console.log("  >_element: ",_element);
		_configAPI.init(wifiboxURL,wifiboxCGIBinURL);
	};
	
	//this.readForm = function(form) {
	this.readForm = function(form) {
		//console.log("FormPanel:readForm");
		if(!form) form = _element; // if no form specified, read whole panel form
		//console.log("FormPanel");
		var settings = {};
		// Read all selects
		var selects = form.find("select");
		selects.each( function(index,element) {
			var elem = $(element);
			//var fieldName = elem.attr('name');
			if(elem.attr('name') != "") {
				settings[elem.attr('name')] = elem.val();
			}
		});
		// Read all inputs
		var inputs = form.find("input");
		inputs.each( function(index,element) {
			var elem = $(element);
			if(elem.attr('name') != "") {
				switch(elem.attr("type")) {
				case "text":
				case "number":
					settings[elem.attr('name')] = elem.val();
					break;
				case "checkbox":
					settings[elem.attr('name')] = elem.prop('checked');
					break;
				}
			}
		});
		// Read all textareas
		var textareas = form.find("textarea");
		textareas.each( function(index,element) {
			var elem = $(element);
			settings[elem.attr('name')] = elem.val();
		});
		return settings;
	};
	
	this.fillForm = function(settings,form) { 
		//console.log("FormPanel:fillForm");
		if(!form) form = _element; // if no form specified, fill whole panel form
		//console.log("  form: ",form);
		
		clearValidationErrors();
		
		//fill form with loaded settings
		var selects = form.find("select");
		selects.each( function(index,element) {
			var elem = $(element);
			elem.val(settings[elem.attr('name')]);
		});
		var inputs = form.find("input");
		inputs.each( function(index,element) {
			var elem = $(element);
			//console.log("printer setting input: ",index,element.attr("type"),element.attr('name')); //,element);
			switch(elem.attr("type")) {
			case "text":
			case "number":
				elem.val(settings[elem.attr('name')]);
				break;
			case "checkbox":
				elem.prop('checked', settings[elem.attr('name')]);
				break;
			}
		});
		var textareas = form.find("textarea");
		textareas.each( function(index,element) {
			var elem = $(element);
			var value = settings[elem.attr('name')];
			// console.log(className,'fillForm textarea set value',value);
			elem.val(value);
		});
	};
	
	this.saveSettings = function(newSettings,complete) {
		console.log("  newSettings: ",newSettings);
		_configAPI.save(newSettings,function(data) {
			var validation = data.validation;
			//console.log("  validation: ",validation);
			clearValidationErrors();
			var validated = true;
			$.each(validation, function(key, val) {
				if (val != "ok") {
					console.log("ERROR: setting '" + key + "' not successfully set. Message: " + val);
					displayValidationError(key,val);
					validated = false;
				}
			});
			if(complete) complete(validated, data);
		}, function() {
			console.log("Settings:saveSettings: failed");
			clearTimeout(_retrySaveSettingsDelay);
			_retrySaveSettingsDelay = setTimeout(function() { _self.saveSettings(newSettings,complete); },_retryDelay); // retry after delay
		});
	};
	function displayValidationError(key,msg) {
		var formElement = _element.find("[name|='"+key+"']");
		formElement.addClass("error");
		var errorMsg = "<p class='errorMsg'>"+msg+"</p>";
		formElement.after(errorMsg);
	};
	function clearValidationErrors() {
		_element.find(".errorMsg").remove();
		_element.find(".error").removeClass("error");
	};
	
	this.loadAllSettings = function(complete) {
		_configAPI.loadAll(complete,function() {
			clearTimeout(_retryLoadAllSettingsDelay);
			_retryLoadAllSettingsDelay = setTimeout(function() { _self.loadAllSettings(complete); },_retryDelay); // retry after delay
		});
	};
	this.loadSettings = function(targetSettings,complete) {
		// console.log(className,'loadSettings',targetSettings);
		_configAPI.load(targetSettings,complete,function() {
			clearTimeout(_retryLoadSettingsDelay);
			_retryLoadSettingsDelay = setTimeout(function() { _self.loadSettings(targetSettings,complete); },_retryDelay); // retry after delay
		});
	};
	
	this.resetAllSettings = function(complete) {
		_configAPI.resetAll(complete,function() { 
			clearTimeout(_retryResetSettingsDelay);
			_retryResetSettingsDelay = setTimeout(function() { _self.resetAllSettings(complete); },_retryDelay); // retry after delay
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

function NetworkPanel() {
	var className = 'NetworkPanel';
	var NOT_CONNECTED = "not connected"; // used as first item in networks list
	
	// network mode
	NetworkPanel.NETWORK_MODE = {
		NEITHER: "neither",
		CLIENT: "clientMode",
		ACCESS_POINT: "accessPointMode"
	};
	var _networkMode = NetworkPanel.NETWORK_MODE.NEITHER;
	var _networkModeChangedHandler;
	
	var _form = new FormPanel();
	var _api = new NetworkAPI();
	var _networks = {};
	var _currentNetwork;					// the ssid of the network the box is on
	var _selectedNetwork;         // the ssid of the selected network in the client mode settings
	var _substituted_ssid;				// the substituted ssid (displayed during creation)
	var _currentLocalIP = "";
	var _currentAP;
	var _currentNetworkStatus;
	
	var _retryDelay = 2000;
	//var _retryRefreshNetworksDelay;
	var _retryRetrieveStatusDelayTime = 1000;
	var _retryRetrieveStatusDelay;
	// after switching wifi network or creating a access point we delay the status retrieval
	// because the webserver needs time to switch
	var _retrieveNetworkStatusDelayTime = 1000;
	var _retrieveNetworkStatusDelay;
	
	// ui elements
	var _element;
	var _networkSelector;
	var _apFieldSet;
	var _clientFieldSet;
	var _apRadioButton;
	var _clientRadioButton;
	var _btnRefresh
	var _btnConnect;
	var _btnCreate;
	var _passwordField;
	var _passwordLabel;
	var _clientStateDisplay;
	var _apModeStateDisplay;
	
	var _self = this;
	
	this.init = function(wifiboxURL,wifiboxCGIBinURL,panelElement) {
		//console.log("NetworkPanel:init");
		
		_form.init(wifiboxURL,wifiboxCGIBinURL,panelElement)
		
		_api.init(wifiboxURL,wifiboxCGIBinURL);
		
		_element = panelElement;
		_apRadioButton			= _element.find("#ap");
		_clientRadioButton	= _element.find("#client");
		_btnRefresh		 			= _element.find("#refreshNetworks");
		_btnConnect 				= _element.find("#connectToNetwork");
		_btnCreate 					= _element.find("#createAP");
		_networkSelector 		= _element.find("#network");
		_apFieldSet 				= _element.find("#apSettings");
		_clientFieldSet 		= _element.find("#clientSettings");
		_passwordField 			= _element.find("#password");
		_passwordLabel 			= _element.find("#passwordLabel");
		_clientStateDisplay = _element.find("#clientModeState");
		_apModeStateDisplay = _element.find("#apModeState");
		
		_apRadioButton.parent().on('touchstart mousedown',showAPSettings);
		_clientRadioButton.parent().on('touchstart mousedown',showClientSettings);
		_btnRefresh.on('touchstart mousedown',onRefreshClick);
		_btnConnect.on('touchstart mousedown',_self.connectToNetwork);
		_btnCreate.on('touchstart mousedown',_self.createAP);
		_networkSelector.change(networkSelectorChanged);
	}
	/*
	 * Handlers
	 */
	function showAPSettings() {
		_apFieldSet.show();
		_clientFieldSet.hide();
	};
	function showClientSettings() {
		_clientFieldSet.show();
		_apFieldSet.hide();
	};
	function onRefreshClick() {
		_btnRefresh.attr("disabled", true);
		_self.refreshNetworks(function() {
			_btnRefresh.removeAttr("disabled");
		})
	}
	function networkSelectorChanged(e) {
		var selectedOption = $(this).find("option:selected");
		_self.selectNetwork(selectedOption.val());
	};

	this.update = function() {
		//console.log("NetworkPanel:update");
		_self.refreshNetworks();
		_self.retrieveNetworkStatus(false);
	}
	this.refreshNetworks = function(completeHandler) {
		if (limitedFeatures) {
			console.log(className,'ignoring refreshNetworks due to limitedFeatures mode');
			return; //don't check printer status when in limitedFeatures mode
		}
		
		//console.log("NetworkPanel:refreshNetworks");
		_api.scan(function(data) { // completed
			//console.log("NetworkPanel:scanned");
			_networks = {};
			var foundCurrentNetwork = false;
			// fill network selector
			_networkSelector.empty();
			_networkSelector.append(
					$("<option></option>").val(NOT_CONNECTED).html(NOT_CONNECTED)
			);
			$.each(data.networks, function(index,element) {
				if(element.ssid == _currentNetwork) {
					foundCurrentNetwork = true;
				}
				_networkSelector.append(
						$("<option></option>").val(element.ssid).html(element.ssid)
				);
				_networks[element.ssid] = element;
			});
			if(foundCurrentNetwork) {
				_networkSelector.val(_currentNetwork);
				_self.selectNetwork(_currentNetwork);
			}
			if(completeHandler) completeHandler();
		}/*,
		function() { // failed
			clearTimeout(_retryRefreshNetworksDelay);
			_retryRetrieveStatusDelay = setTimeout(function() { _self.refreshNetworks(completeHandler); },_retryDelay); // retry after delay
		}*/);
	};
	
	this.retrieveNetworkStatus = function(connecting) {

		if (limitedFeatures) {
			console.log(className,'ignoring retrieveNetworkStatus due to limitedFeatures mode');
			return; //don't check network status when in limitedFeatures mode
		}

		//console.log("NetworkPanel:retrieveNetworkStatus");

		_api.status(function(data) {
			if(data.status === "") {
				data.status = NetworkAPI.STATUS.CREATED.toString();
			}
			if(typeof data.status === 'string') {
				data.status = parseInt(data.status);
			}
			//console.log("NetworkPanel:retrievedStatus status: ",data.status,data.statusMessage);
			
			// if status changed
			if(data.status != _currentNetworkStatus) {
				// Determine which network mode ui to show
				switch(data.status) {
					case NetworkAPI.STATUS.NOT_CONNECTED:
						setNetworkMode(NetworkPanel.NETWORK_MODE.NEITHER);
						break;
					case NetworkAPI.STATUS.CONNECTING_FAILED:
					case NetworkAPI.STATUS.CONNECTING:
					case NetworkAPI.STATUS.CONNECTED:
						setNetworkMode(NetworkPanel.NETWORK_MODE.CLIENT);
						break;
					case NetworkAPI.STATUS.CREATING:
					case NetworkAPI.STATUS.CREATED:
						setNetworkMode(NetworkPanel.NETWORK_MODE.ACCESS_POINT);
						break;
				}
				// update info
				switch(data.status) {
					case NetworkAPI.STATUS.CONNECTED:
						_currentNetwork = data.ssid;
						_currentLocalIP = data.localip;
						_self.selectNetwork(data.ssid);
						break;
					case NetworkAPI.STATUS.CONNECTING_FAILED:
					case NetworkAPI.STATUS.CONNECTING:
						_currentLocalIP = "";
						break;
					case NetworkAPI.STATUS.CREATING:
					case NetworkAPI.STATUS.CREATED:					
						_currentNetwork = undefined;
						_self.selectNetwork(NOT_CONNECTED);
						if(data.ssid && data.status == NetworkAPI.STATUS.CREATED) {
							_currentAP = data.ssid;
						}
						break;
				}
				// update ui 
				updateClientModeUI(data.status,data.statusMessage);
				updateAPModeUI(data.status,"");
			}

			// Keep checking for updates?
			if(connecting) {
				switch(data.status) {
				case NetworkAPI.STATUS.CONNECTING:
				case NetworkAPI.STATUS.CREATING:
					clearTimeout(_retryRetrieveStatusDelay);
				  _retryRetrieveStatusDelay = setTimeout(function() { _self.retrieveNetworkStatus(connecting); },_retryRetrieveStatusDelayTime); // retry after delay
					break;
				}
			}
			_currentNetworkStatus = data.status;
		}, function() {
			//console.log("NetworkPanel:retrieveStatus failed");
			clearTimeout(_retryRetrieveStatusDelay);
			_retryRetrieveStatusDelay = setTimeout(function() { _self.retrieveNetworkStatus(connecting); }, _retryRetrieveStatusDelayTime); // retry after delay
		});
	};
	function setNetworkMode(mode) {
		//console.log("NetworkPanel:setNetworkMode: ",_networkMode,">",mode);
		if(mode == _networkMode) return;
		switch(mode) {
			case NetworkPanel.NETWORK_MODE.NEITHER:
				_apFieldSet.show();
				_clientFieldSet.show();
				break;
			case NetworkPanel.NETWORK_MODE.CLIENT:
				_clientRadioButton.prop('checked',true);
				_apFieldSet.hide();
				_clientFieldSet.show();
				break;
			case NetworkPanel.NETWORK_MODE.ACCESS_POINT:
				_apRadioButton.prop('checked',true);
				_apFieldSet.show();
				_clientFieldSet.hide();
				break;
		}
		_networkMode = mode;
		if(_networkModeChangedHandler) _networkModeChangedHandler(_networkMode);
	}
	
	this.selectNetwork = function(ssid) {
		//console.log("NetworkPanel:selectNetwork: ",ssid);
		if(ssid == "") return;
		_selectedNetwork = ssid;

		var network = _networks[ssid];
		if(network === undefined || network.encryption == "none") {
			_passwordLabel.hide();
			_passwordField.hide();
		} else {
			_passwordLabel.show();
			_passwordField.show();
		}
		_passwordField.val("");
	};
	
	function updateClientModeUI(state,statusMessage) {
		//console.log("NetworkPanel:updateClientModeUI ",state,statusMessage);
		var msg = "";
		switch(state) {
			case NetworkAPI.STATUS.NOT_CONNECTED:
			case NetworkAPI.STATUS.CREATING:
			case NetworkAPI.STATUS.CREATED:
				_btnConnect.removeAttr("disabled");
				msg = "Not connected";
				_networkSelector.val(NOT_CONNECTED);
				break;
			case NetworkAPI.STATUS.CONNECTED:
				_btnConnect.removeAttr("disabled");
				msg = "Connected to: <b>"+_currentNetwork+"</b>.";
				if(_currentLocalIP != undefined && _currentLocalIP != "") {
					var a = "<a href='http://"+_currentLocalIP+"' target='_black'>"+_currentLocalIP+"</a>";
					msg += " (IP: "+a+")";
				}
				_networkSelector.val(_currentNetwork);
				break;
			case NetworkAPI.STATUS.CONNECTING:
				_btnConnect.attr("disabled", true);
				msg = "Connecting... Reconnect by connecting your device to <b>"+_selectedNetwork+"</b> and going to <a href='http://connect.doodle3d.com'>connect.doodle3d.com</a>";
				break;
			case NetworkAPI.STATUS.CONNECTING_FAILED:
				_btnConnect.removeAttr("disabled");
				msg = statusMessage;
				break;
		}
		//console.log("  client display msg: ",msg);
		_clientStateDisplay.html(msg);
	};
	function updateAPModeUI(state,statusMessage) {
		var msg = "";
		switch(state) {
			case NetworkAPI.STATUS.CONNECTING_FAILED:
			case NetworkAPI.STATUS.NOT_CONNECTED:
			case NetworkAPI.STATUS.CONNECTING:
			case NetworkAPI.STATUS.CONNECTED:
				_btnCreate.removeAttr("disabled");
				msg = "Not currently a access point";
				break;
			case NetworkAPI.STATUS.CREATED:
				_btnCreate.removeAttr("disabled");
				msg = "Is access point: <b>"+_currentAP+"</b>";
				break;
			case NetworkAPI.STATUS.CREATING:
				_btnCreate.attr("disabled", true);
				msg = "Creating access point... Reconnect by connecting your device to <b>"+_substituted_ssid+"</b> and going to <a href='http://draw.doodle3d.com'>draw.doodle3d.com</a>";
				break;
		}
		//console.log("  ap display msg: ",msg);
		_apModeStateDisplay.html(msg);
	};

	this.connectToNetwork = function() {
		//console.log("NetworkPanel:connectToNetwork");
		if(_selectedNetwork == undefined) return;
		// save network related settings and on complete, connect to network
		_form.saveSettings(_form.readForm(),function(validated, data) {
			if(!validated) return;
			updateClientModeUI(NetworkAPI.STATUS.CONNECTING,"");
			_api.associate(_selectedNetwork,_passwordField.val(),true);
			
			// after switching wifi network or creating a access point we delay the status retrieval
			// because the webserver needs time to switch it's status
			clearTimeout(_retrieveNetworkStatusDelay);
			_retrieveNetworkStatusDelay = setTimeout(function() { _self.retrieveNetworkStatus(true); }, _retrieveNetworkStatusDelayTime);
		});
	};

	this.createAP = function() {
		//console.log("createAP");
		// save network related settings and on complete, create access point
		_form.saveSettings(_form.readForm(),function(validated, data) {
			if(!validated) return;
			_substituted_ssid = data.substituted_ssid;
			updateAPModeUI(NetworkAPI.STATUS.CREATING,""); 
			_api.openAP();

			// after switching wifi network or creating a access point we delay the status retrieval
			// because the webserver needs time to switch it's status
			clearTimeout(_retrieveNetworkStatusDelay);
			_retrieveNetworkStatusDelay = setTimeout(function() { _self.retrieveNetworkStatus(true); }, _retrieveNetworkStatusDelayTime);
		});
	};
	
	this.setNetworkModeChangedHandler = function(handler) {
		_networkModeChangedHandler = handler;
	}
}

/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

function PrinterPanel() {
	
	this.printerType;
	var _api = new PrinterAPI();
	var _form = new FormPanel();
	
	// ui elements
	var _element;
	var _printerSelector;
	var _printerSettings;
	
	var _self = this;
	
	this.init = function(wifiboxURL,wifiboxCGIBinURL,panelElement) {
		
		_form.init(wifiboxURL,wifiboxCGIBinURL,panelElement)
		_api.init(wifiboxURL,wifiboxCGIBinURL);
		_element = panelElement;
		_printerSelector 	= _element.find("#printerType");
		_printerSelector.change(_self.printerSelectorChanged);
		
		// we use readForm to get all the settings we need to 
		// reload after changing printer type 
		_printerSettings = _form.readForm();
		
		var gcodePanel = _element.find("#gcodePanel");
		gcodePanel.coolfieldset({collapsed:true});
	}
	this.load = function(completeHandler) {
		
		_api.listAll(function(data) {
			$.each(data.printers, function(key, value) {
				// console.log(key,value);
				$('#printerType').append($('<option>').text(value).attr('value', key));
			});
			completeHandler();
		});
	}
	this.printerSelectorChanged = function(e) {
		_self.printerType = _printerSelector.find("option:selected").val();
		var settings = {}; 
		settings[_printerSelector.attr("name")] = _self.printerType;
		
		_form.saveSettings(settings,function(validated) {
			if(!validated) return;
			_form.loadSettings(_printerSettings,function(settings) {
				_form.fillForm(settings);
			});
		});
	}
}

/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

//these settings are defined in the firmware (conf_defaults.lua) and will be initialized in loadSettings()
//var settings = {};
var settingsPopup;
//wrapper to prevent scoping issues in showSettings()
function openSettingsWindow() {
	settingsWindow.loadSettings(function() { // reload settings
		settingsPopup.open();
	});
}

function SettingsWindow() {
	
	var _window;
	var _btnOK;
	
	var _wifiboxURL;
	var _restoredStateHideDelayTime = 3000;
	var _restoredStateHideDelay; // setTimout instance

	// Events
	SettingsWindow.SETTINGS_LOADED 		= "settingsLoaded";
	
	var _form = new FormPanel();
	var _updatePanel = new UpdatePanel();
	var _printerPanel = new PrinterPanel();
	var _networkPanel = new NetworkPanel();
	var _networkAPI = new NetworkAPI();
	
	var _restoreStateField
	
	var self = this;

	this.init = function(wifiboxURL,wifiboxCGIBinURL) {
		
		_wifiboxURL = wifiboxURL;

		_window = $("#popupSettings");
		_btnOK = _window.find(".btnOK");
		settingsPopup = new Popup($("#popupSettings"), $("#popupMask"));
		settingsPopup.setEnterEnabled(false);
		settingsPopup.setAutoCloseEnabled(false);
		
		_btnOK.on('touchstart mousedown',settingsPopup.commit);
		$("#popupSettings").bind("onPopupCancel", function() { settingsPopup.close(); } );
		$("#popupSettings").bind("onPopupCommit", self.submitwindow);
		
		_networkAPI.init(wifiboxURL,wifiboxCGIBinURL);
		
		// Load external settings.html into SettingsWindow
		_window.find("#settingsContainer").load("settings.html", function() {
			console.log("Settings:finished loading settings.html");

			var formElement = _window.find("form");
			formElement.submit(function (e) { self.submitwindow(e); });
			
			_form.init(wifiboxURL,wifiboxCGIBinURL,formElement);
			
			// printer panel
			var printerPanelElement = formElement.find("#printerPanel");
			_printerPanel.init(wifiboxURL,wifiboxCGIBinURL,printerPanelElement);
			
			// Load printer types list 
			// First, because after the settings are loaded the printer type need to be selected 
			_printerPanel.load(function() {
				
				_restoreStateField	= formElement.find("#restoreState");
				self.btnRestoreSettings	= formElement.find("#restoreSettings");
				self.btnRestoreSettings.on('touchstart mousedown',self.resetSettings);

				// network panel
				var $networkPanelElement = formElement.find("#networkPanel");
				_networkPanel.init(wifiboxURL,wifiboxCGIBinURL,$networkPanelElement);
				
				
				// update panel
				var updatePanelElement = formElement.find("#updatePanel");
				_updatePanel.init(wifiboxURL,updatePanelElement);
				_networkPanel.setNetworkModeChangedHandler(function(networkMode) {
					var inAccessPointMode = (networkMode == NetworkPanel.NETWORK_MODE.ACCESS_POINT);
					_updatePanel.setInAccessPointMode(inAccessPointMode);
				});
				
				self.loadSettings();
				
			});
		}); //this.window.find
	}; //this.init
	
	this.openSettings = function() {
		self.loadSettings(function() { // reload settings
			settingsPopup.open();
		});
	};
	
//	this.closeSettings = function(complete) {
//		settingsPopup.close(complete);
//	};

	this.submitwindow = function(e) {
		_btnOK.attr("disabled",true);
		e.preventDefault();
		e.stopPropagation();
		var newSettings = _form.readForm();
		_form.saveSettings(newSettings,function(validated, data){
			if(validated) {
				settings = newSettings; // store new settings in global settings
				settingsPopup.close();
				self.signin();
			}
			_btnOK.removeAttr("disabled");
		});
	};
	
	this.loadSettings = function(complete) {
		_form.loadAllSettings(function(loadedSettings){
			console.log("Settings:loaded settings: ",loadedSettings);
			settings = loadedSettings;
			_form.fillForm(settings);
			$(document).trigger(SettingsWindow.SETTINGS_LOADED);
			if(complete) complete();
		});
		_networkPanel.update();
	};
	
	this.resetSettings = function() {
		console.log("resetSettings");
		self.btnRestoreSettings.attr("disabled", true);
		clearTimeout(_restoredStateHideDelay);
		self.setRestoreState("Restoring...");
		_form.resetAllSettings(function(restoredSettings) { 
			//console.log("  settings: ",restoredSettings);
			settings = restoredSettings;
			_form.fillForm(restoredSettings);
			$(document).trigger(SettingsWindow.SETTINGS_LOADED);

			self.btnRestoreSettings.removeAttr("disabled");
			self.setRestoreState("Settings restored");
			// auto hide status
			clearTimeout(_restoredStateHideDelay);
			_restoredStateHideDelay = setTimeout(function() { self.setRestoreState("");	},_restoredStateHideDelayTime);
		});
	};
	
	this.setRestoreState = function(text) {
		_restoreStateField.html(text);
	};

	this.signin = function() {
		_networkAPI.signin();
	};

	this.downloadlogs = function() {
		window.location.href = _wifiboxURL + "/info/logfiles";
	};

	this.downloadGcode = function() {
		var gcode = generate_gcode();
		if (gcode!=undefined) {
			var blob = new Blob([gcode.join("\n")], {type: "text/plain;charset=utf-8"});
			saveAs(blob, "doodle3d.gcode");
		}
	};

	this.downloadSvg = function() {
		var svg = saveToSvg();
		if (svg!=undefined) {
			var blob = new Blob([svg], {type: "text/plain;charset=utf-8"});
			saveAs(blob, "doodle3d.svg");
		}
	};

	this.openFileManager = function() {
		location.href = "filemanager/"+location.search;
	}
}

/*************************
 *
 *
 *  FROM DOODLE3D.INI
 *
 */

//TODO: find all references to these variables, replace them and finally remove these.
var objectHeight = 20;
var layerHeight = .2;
//var wallThickness = .5;
//var hop = 0;
//var speed = 70;
//var travelSpeed = 200;
var enableTraveling = true;
//var filamentThickness = 2.89;
var minScale = .3;
var maxScale = 1;
var shape = "%";
var twists = 0;
//var useSubLayers = true;
//var debug = false; // debug moved to main.js
var loglevel = 2;
//var zOffset = 0;
var serverport = 8888;
var autoLoadImage = "hand.txt";
var loadOffset = [0, 0]; // x en y ?
var showWarmUp = true;
var loopAlways = false;
var firstLayerSlow = true;
var useSubpathColors = false;
var autoWarmUp = true;
//var maxObjectHeight = 150;
var maxScaleDifference = .1;
var frameRate = 60;
var quitOnEscape = true;
var screenToMillimeterScale = .3; // 0.3
//var targetTemperature = 220;
//var simplifyiterations = 10;
//var simplifyminNumPoints = 15;
//var simplifyminDistance = 3;
//var retractionspeed = 50;
//var retractionminDistance = 5;
//var retractionamount = 3;
var sideis3D = true;
var sidevisible = true;
var sidebounds = [900, 210, 131, 390];
var sideborder = [880, 169, 2, 471];
var windowbounds = [0, 0, 800, 500];
var windowcenter = true;
var windowfullscreen = false;
var autoWarmUpCommand = "M104 S230";
//var checkTemperatureInterval = 3;
var autoWarmUpDelay = 3;
/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

function UpdatePanel() {
	var className = 'UpdatePanel';
	var _form = new FormPanel();

	this.wifiboxURL;
	this.element;

	this.statusCheckInterval = 1000;
	this.statusCheckDelayer; 			// setTimout instance
	this.installedDelay = 90*1000; 		// Since we can't retrieve status during installation we show the installed text after a fixed delay
	this.installedDelayer; 				// setTimout instance
	this.retryDelay = 1000;
	this.retryDelayer; 					// setTimout instance
	//this.timeoutTime = 3000;

	this.canUpdate = false;
	this.currentVersion = "";
	this.newestVersion;
	this.currentReleaseDate;
	this.newestReleaseDate;
	this.progress;
	this.imageSize;
	var _inAccessPointMode;

	// states from api, see Doodle3D firmware src/script/d3d-updater.lua
	UpdatePanel.NONE 			= 1; // default state
	UpdatePanel.DOWNLOADING  	= 2;
	UpdatePanel.DOWNLOAD_FAILED	= 3;
	UpdatePanel.IMAGE_READY 	= 4; // download successful and checked
	UpdatePanel.INSTALLING 		= 5;
	UpdatePanel.INSTALLED 		= 6;
	UpdatePanel.INSTALL_FAILED 	= 7;

	this.state; // update state from api
	this.stateText = ""; // update state text from api

	var self = this;

	this.init = function(wifiboxURL,updatePanelElement) {
		_form.init(wifiboxURL,wifiboxURL,updatePanelElement);

		this.wifiboxURL = wifiboxURL;

		this.element = updatePanelElement;
		this.retainCheckbox = this.element.find("#retainConfiguration");
		this.includeBetasCheckbox = this.element.find("#includeBetas");
		this.btnUpdate = this.element.find("#update");
		this.statusDisplay = this.element.find("#updateState");
		this.infoDisplay = this.element.find("#updateInfo");

		this.retainCheckbox.change(this.retainChanged);
		this.includeBetasCheckbox.change(this.includeBetasChanged);
		this.btnUpdate.click(this.update);

		this.checkStatus(false);
	}

	this.retainChanged = function(e) {
		//console.log("UpdatePanel:retainChanged");
		//this call ensures that the update button gets enabled if (!retainChanged && !canUpdate)
		self.setState(self.state,true);
	}

	this.includeBetasChanged = function() {
		//console.log("UpdatePanel:includeBetasChanged");
		_form.saveSettings(_form.readForm(),function(validated, data) {
			if(validated) self.checkStatus(false);
		});
	}


	this.update = function() {
		console.log("UpdatePanel:update");
		self.downloadUpdate();
	}

	this.downloadUpdate = function() {
		console.log("UpdatePanel:downloadUpdate");
		$.ajax({
			url: self.wifiboxURL + "/update/download",
			type: "POST",
			dataType: 'json',
			success: function(response){
				console.log("UpdatePanel:downloadUpdate response: ",response);
			}
		}).fail(function() {
			console.log("UpdatePanel:downloadUpdate: failed");
		});
		self.setState(UpdatePanel.DOWNLOADING);
		self.startCheckingStatus();
	}

	this.installUpdate = function() {
		console.log("UpdatePanel:installUpdate");

		// should personal sketches and settings be retained over update?
		var retain = self.retainCheckbox.prop('checked');
		console.log("  retain: ",retain);

		self.stopCheckingStatus();
		postData = {no_retain:!retain}
		$.ajax({
			url: self.wifiboxURL + "/update/install",
			type: "POST",
			data: postData,
			dataType: 'json',
			success: function(response){
				console.log("UpdatePanel:installUpdate response: ",response);
			}
		}).fail(function() {
			//console.log("UpdatePanel:installUpdate: no respons (there shouldn't be)");
		});
		self.setState(UpdatePanel.INSTALLING);

		clearTimeout(self.installedDelayer);
		self.installedDelayer = setTimeout(function() { self.setState(UpdatePanel.INSTALLED) },self.installedDelay);
	}


	this.startCheckingStatus = function() {
		clearTimeout(self.statusCheckDelayer);
		clearTimeout(self.retryDelayer);
		self.statusCheckDelayer = setTimeout(function() { self.checkStatus(true) },self.statusCheckInterval);
	}

	this.stopCheckingStatus = function() {
		clearTimeout(self.statusCheckDelayer);
		clearTimeout(self.retryDelayer);
	}

	this.checkStatus = function(keepChecking) {
		if (limitedFeatures) {
			console.log(className,'ignoring checkStatus due to limitedFeatures mode');
			return; //don't check printer status when in limitedFeatures mode
		}

		if (!communicateWithWifibox) return;
		$.ajax({
			url: self.wifiboxURL + "/update/status",
			type: "GET",
			dataType: 'json',
			//timeout: self.timeoutTime,
			success: function(response){
				console.log("UpdatePanel:checkStatus response: ",response);

				// Keep checking ?
				if(keepChecking) {
					switch(self.state){
						case UpdatePanel.DOWNLOADING:
						case UpdatePanel.INSTALLING:
							clearTimeout(self.statusCheckDelayer);
							self.statusCheckDelayer = setTimeout(function() { self.checkStatus(keepChecking) },self.statusCheckInterval);
							break;
					}
				}

				if(response.status != "error") {
					var data = response.data;
					self.handleStatusData(data);
				} else {
					console.log("API update/status call returned an error: '" + response.msg + "'");
				}
			}
		}).fail(function() {
			//console.log("UpdatePanel:checkStatus: failed");
			if(keepChecking) {
				clearTimeout(self.retryDelayer);
				self.retryDelayer = setTimeout(function() { self.checkStatus(keepChecking) },self.retryDelay); // retry after delay
			}
		});
	}


	this.handleStatusData = function(data) {
		//console.log("UpdatePanel:handleStatusData");
		//status texts and button state might have to be updated if the newest version changes (e.g., after (un)ticking include betas checkbox)
		var refreshUI = (self.newestVersion != data.newest_version);

		self.canUpdate 				= data.can_update;

		if(self.currentVersion != data.current_version || self.newestVersion != data.newest_version) {
			self.currentVersion 	= data.current_version;
			self.newestVersion 		= data.newest_version;
			self.currentReleaseDate	= data.current_release_date; // not always available (for older versions)
			self.newestReleaseDate	= data.newest_release_date; // not always available (for older versions)
			self.updateInfoDisplay();
		}

		self.stateText 				= data.state_text;
		self.progress 				= data.progress; // not always available
		self.imageSize 				= data.image_size; // not always available

		self.setState(data.state_code, refreshUI);

		switch(this.state){
			case UpdatePanel.IMAGE_READY:
				self.installUpdate();
				break;
		}
	}

	this.setState = function(newState,refresh) {
		//console.log("UpdatePanel:setState");
		if(!refresh && this.state == newState) return;
		console.log("UpdatePanel:setState: ",this.state," > ",newState,"(",this.stateText,") (in Access Point Mode: ",_inAccessPointMode,") (newestVersion: ",self.newestVersion,") (refresh: ",refresh,")");
		this.state = newState;

		// should personal sketches and settings be retained over update?
		var retain = self.retainCheckbox.prop('checked');
		//console.log("  retain", retain);

		// download button
		// if there isn't newestVersion data something went wrong,
		//   probably accessing the internet
		//console.log("  self.newestVersion: ",self.newestVersion);
		if(self.newestVersion != undefined) {
			//console.log("  this.state: ",this.state);
			switch(this.state){
				case UpdatePanel.NONE:
				case UpdatePanel.DOWNLOAD_FAILED:
				case UpdatePanel.INSTALL_FAILED:
					//console.log("  self.canUpdate: ",self.canUpdate);
					if(self.canUpdate || !retain) {
						self.btnUpdate.removeAttr("disabled");
					} else {
						self.btnUpdate.attr("disabled", true);
					}
					break;
				default:
					self.btnUpdate.attr("disabled", true);
				break;
			}
		} else {
			self.btnUpdate.attr("disabled", true);
		}
		this.updateStatusDisplay();
	}

	this.updateStatusDisplay = function() {
		var text = "";
		if(self.newestVersion != undefined) {
			switch(this.state){
				case UpdatePanel.NONE:
					if(self.canUpdate) {
						var currIsBeta = self.versionIsBeta(self.currentVersion);
						var newIsBeta = self.versionIsBeta(self.newestVersion);
						var relIsNewer = (self.newestReleaseDate && self.currentReleaseDate) ? (self.newestReleaseDate - self.currentReleaseDate > 0) : true;

						if (!newIsBeta) {
							if (relIsNewer) text = "Update available.";
							else text = "You can switch back to the latest stable release."; //this case is always a beta->stable 'downgrade'
						} else {
							//NOTE: actually, an older beta will never be presented as update by the API
							var prefixText = currIsBeta ? "A" : (relIsNewer ? "A newer" : "An older");
							text = prefixText + " beta release is available.";
						}
					} else {
						text = "You're up to date.";
					}
					break;
				case UpdatePanel.DOWNLOADING:
					text = "Downloading update...";
					break;
				case UpdatePanel.DOWNLOAD_FAILED:
					text = "Downloading update failed.";
					break;
				case UpdatePanel.IMAGE_READY:
					text = "Update downloaded.";
					break;
				case UpdatePanel.INSTALLING:
					text = "Installing update... (will take a minute)";
					break;
				case UpdatePanel.INSTALLED:
					//text = "Update complete, please reconnect by connecting your device to the access point of your WiFi box and going to <a href='http://draw.doodle3d.com'>draw.doodle3d.com</a>";
					text = "Update complete, please <a href='javascript:location.reload(true);'>refresh Page</a>.";
					break;
				case UpdatePanel.INSTALL_FAILED:
					text = "Installing update failed.";
					break;
			}
		} else {
			if(_inAccessPointMode) {
				text = "Can't access internet in access point mode.";
			} else {
				text = "Can't access internet.";
			}
		}
		this.statusDisplay.html(text);
	}

	this.updateInfoDisplay = function() {
		var html = 'Current version: ' + self.currentVersion;
		if (self.currentReleaseDate) html += '; released: ' + self.formatDate(self.currentReleaseDate);
		html += ' (<a target="d3d-curr-relnotes" href="ReleaseNotes.html">release notes</a>).';

		if(self.canUpdate) {
			html += '<br/>Latest version: ' + self.newestVersion;
			if (self.newestReleaseDate) html += '; released: ' + self.formatDate(self.newestReleaseDate);
			html += ' (<a target="d3d-new-relnotes" href="http://doodle3d.com/updates/images/ReleaseNotes.md">release notes</a>).';
		}
		self.infoDisplay.html(html);
	}


	this.setInAccessPointMode = function(inAccessPointMode) {
		_inAccessPointMode = inAccessPointMode;
		self.updateStatusDisplay();
	}

	this.formatDate = function(ts) {
		if (!ts || ts.length != 8 || !/^[0-9]+$/.test(ts)) return null;
		var fields = [ ts.substr(0, 4), ts.substr(4, 2), ts.substr(6, 2) ];
		if (!fields || fields.length != 3 || fields[1] > 12) return null;

		var abbrMonths = [ 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Sep', 'Aug', 'Oct', 'Nov', 'Dec' ];
		return abbrMonths[fields[1] - 1] + " " + fields[2] + ", " + fields[0];
	}

	this.versionIsBeta = function(version) {
		return version ? /.*-.*/g.test(version) : null;
	}
}

//var shapeResolution=3;
var shapePopup;

function initScanDialog() {
  scanPopup = new Popup($("#popupScan"), $("#popupMask"));
  $("#btnScanOk").on("onButtonClick", onBtnScanOk);
  $("#btnCloseScan").on("onButtonClick", onBtnCloseScan);
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
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

var grandTour;
function GrandTour(_name) {
  //console.log("GrandTour");
  this.tour = "";
  this.name = _name;
  this.active = false;
  var self = this;

  this.init = function() {
    //console.log("GrandTour >> f:init()");

    this.tour = function() {
      $('#help_d3dIntro').joyride({
        autoStart: false,
        modal: true,
        expose: true,
        'tipAdjustmentX': 15,
        'tipAdjustmentY': 15,
        'tipLocation': 'bottom',         // 'top' or 'bottom' in relation to parent
        'nubPosition': 'auto',           // override on a per tooltip bases
        'scrollSpeed': 300,              // Page scrolling speed in ms
        //      'timer': 2000,                   // 0 = off, all other numbers = time(ms)
//        'startTimerOnClick': true,       // true/false to start timer on first click
        'nextButton': true,              // true/false for next button visibility
        'tipAnimation': 'fade',           // 'pop' or 'fade' in each tip
//        'pauseAfter': [],                // array of indexes where to pause the tour after
        'tipAnimationFadeSpeed': 350,    // if 'fade'- speed in ms of transition
//        'cookieMonster': true,           // true/false for whether cookies are used
//        'cookieDomain': false,           // set to false or yoursite.com
//        'cookieName': 'Doodle3DFirstTime',         // choose your own cookie name
        //      'localStorage': true,         //
        //      'localStorageKey': 'Doodle3DFirstTime',         // choose your own cookie name
        'preRideCallback' : self.preRideCallback,
        'preStepCallback': self.preStepCallback,       // A method to call before each step
        'postStepCallback': self.postStepCallback,       // A method to call after each step
        'postRideCallback': self.postRideCallback        // a method to call once the tour closes
      });
    };
    this.tour();
  };

  this.preRideCallback = function(index, tip) {
    //console.log("GrandTour >> f:preRideCallback() >> index: " + index);
    if (index == 0 && $.cookie("Doodle3DFirstTime") == "ridden") {
      //console.log("GrandTour >> f:preRideCallback() >> we've been here before...");

      if ($.cookie("grandTourFinished")) {
        // grand tour was previously finished (eh.. is that useful?)

        // executing this 3 times because there doesn't seem to be a 'go to step X' method
//        $(this).joyride('set_li', false);
        $(this).joyride('set_li', false);
//        $(this).joyride('set_li', false);
      } else {
        $(this).joyride('set_li', false);
      }
    }
    
    // Overrule printer to tour mode, pausing status updates
    printer.overruleState(Printer.TOUR_STATE);
    
    // bring up thermometer and progressbar to explain them
    thermometer.show();
    progressbar.show();
    message.hide();
  };
  this.preStepCallback = function(index, tip) {
//    console.log("GrandTour >> f:preStepCallback() >> index: " + index);
//    console.log("GrandTour >> f:preStepCallback() >> tip: " , tip);
//    console.log("GrandTour >> f:preStepCallback() >> $(this): " , $(this));
//    console.log("GrandTour >> f:preStepCallback() >> tipsettings: " , $(this)[0].tipSettings);

    var dataset = $(this)[0].$li[0].dataset;
    if (dataset.action != undefined) {
      switch (dataset.action) {
        case "showMessage":
          //console.log("    action: showMessage");
          message.set("This is a status message...", Message.NOTICE);
          break;
      }
    }
  };
  this.postStepCallback = function(index, tip) {
    //console.log("GrandTour >> f:postStepCallback() >> index: " + index);
   // var dataset = $(this)[0].$li[0].dataset;
  };
  this.postRideCallback = function(index, tip) {
//    console.log("GrandTour >> f:postRideCallback() >> index: " + index + ", self.active: " + self.active);
//    console.log("GrandTour >> f:postRideCallback() >> this: " , self);

    self.active = false;

    $(document).trigger(helpTours.TOURFINISHED, self.name);

    // hide the elements which were summoned for the purposes of the tour
//    thermometer.hide();
//    progressbar.hide();
//    message.hide();

    // after seeing the grand tour for the first time ever, set cookie 'Doodle3DFirstTime' to true
    if (!$.cookie("Doodle3DFirstTime")) {
      $.cookie("Doodle3DFirstTime", 'ridden', { expires: 365, domain: false, path: '/' });
    }

    if (index < $(this)[0].$tip_content.length - 1) {
      //console.log("GrandTour >> f:postRideCallback() >> tour terminated before its true end");
      // tour wasn't finished

      // tour was ended prematurely. For only the first few visits, nag the user about being able to revisit the tour..
      if (parseInt($.cookie("Doodle3DVisitCounter")) < helpTours.numTimesToShowNagPopup) {
        helpTours.startTour(helpTours.INFOREMINDER, helpTours);
      }
//      infoReminderTour.start();
    } else {
      // tour was finished
      //console.log("GrandTour >> f:postRideCallback() >> tour ended at its true end");
      // we should be at the end...
      if (!$.cookie("grandTourFinished") && parseInt($.cookie("Doodle3DVisitCounter")) < helpTours.numTimesToShowNagPopup) {
        helpTours.startTour(helpTours.INFOREMINDER, helpTours);
      }
      $.cookie("grandTourFinished", 'yes', { expires: 365, domain: false, path: '/' });
    }

  };

  this.start = function() {
    //console.log("GrandTour >> f:start() >> this: " , this);
    this.active = true;
    $(window).joyride('restart');
//    self.tour();
  };
}

var infoReminderTour;
function InfoReminderTour(_name) {
  //console.log("InfoReminderTour");
  this.tour = "";
  this.name = _name;
  this.active = false;
  var self = this;

  this.init = function(callback) {
    //console.log("InfoReminderTour >> f:init()");

    this.tour = function() {
      $('#help_InfoReminder').joyride({
        autoStart: false,
        modal: true,
        expose: true,
        'tipAdjustmentX': 15,
        'tipAdjustmentY': 15,
        'tipLocation': 'bottom',         // 'top' or 'bottom' in relation to parent
        'nubPosition': 'auto',           // override on a per tooltip bases
        'scrollSpeed': 300,              // Page scrolling speed in ms
        'nextButton': true,              // true/false for next button visibility
        'tipAnimation': 'fade',           // 'pop' or 'fade' in each tip
        'tipAnimationFadeSpeed': 350,    // if 'fade'- speed in ms of transition
        'preRideCallback' : self.preRideCallback,
        'postStepCallback': self.postStepCallback,       // A method to call after each step
        'postRideCallback': self.postRideCallback        // a method to call once the tour closes
      });
    }
    this.tour();
    if (callback != undefined) callback();
  };

  this.preRideCallback = function(index, tip) {
    //console.log("InfoReminderTour >> f:preRideCallback() >> index: " + index + ", tip: " , tip);
  };
  this.postStepCallback = function(index, tip) {
    //console.log("InfoReminderTour >> f:postStepCallback() >> index: " + index + ", tip: " , tip);
  };
  this.postRideCallback = function(index, tip) {
    //console.log("InfoReminderTour >> f:postRideCallback() >> index: " + index + ", tip: " , tip);
    this.active = false;
    $(document).trigger(helpTours.TOURFINISHED, self.name);
  };

  this.start = function() {
    //console.log("InfoReminderTour >> f:start()");
    this.active = true;
    $(window).joyride('restart');
//    self.tour();
  };
}

function initHelp() {
  //console.log("f:initHelp()");

  // track number of visits of this user
//  if ($.cookie("Doodle3DVisitCounter") == null) {
//    $.cookie("Doodle3DVisitCounter", '0');
//  } else {
//    $.cookie("Doodle3DVisitCounter", parseInt($.cookie("Doodle3DVisitCounter")) + 1);
//  }

  // load the html file which describes the tour contents
  $("#helpContainer").load("helpcontent.html", function() {
    //console.log("helpContent loaded");

    helpTours = new HelpTours();

    helpTours.init( function () {


      if (parseInt($.cookie("Doodle3DVisitCounter")) < helpTours.numTimesToShowNagPopup) {
        //console.log("initHelp >> Doodle3DFirstTime cookie is set, Doodle3DVisitCounter is < 4");
        if ($.cookie("Doodle3DFirstTime") != "ridden") {
          setTimeout(helpTours.startTour, 750, helpTours.tours.grandTour, helpTours);
        } else {
          setTimeout(helpTours.startTour, 750, helpTours.tours.infoReminderTour, helpTours);
        }
        // remind user of our nifty tour
      } else if (parseInt($.cookie("Doodle3DVisitCounter")) == helpTours.numTimesToShowNagPopup && $.cookie("Doodle3DFirstTime") != "ridden") {
        // remind
        setTimeout(helpTours.startTour, 750, helpTours.tours.infoReminderTour, helpTours);
      }
//            // only trigger starttour if user is seeing Doodle3D for the first time
//      if ($.cookie("Doodle3DFirstTime") != "ridden") {
//        console.log("initHelp >> intro tour has not been given yet > let's go!");
//        setTimeout(helpTours.startTour, 750, helpTours.tours.grandTour, helpTours);
//      } else if (parseInt($.cookie("Doodle3DVisitCounter")) < helpTours.numTimesToShowNagPopup) {
//        console.log("initHelp >> Doodle3DFirstTime cookie is set, Doodle3DVisitCounter is < 4");
//        // remind user of our nifty tour
//        setTimeout(helpTours.startTour, 750, helpTours.tours.infoReminderTour, helpTours);
//      }
    });
  });

}

var helpTours;
function HelpTours() {
  //console.log("HelpTours");

  this.numTimesToShowNagPopup = 2;

  this.WELCOMETOUR    = "welcometour";
  this.INFOREMINDER   = "inforeminder";
  this.TOURFINISHED   = "tourfinished";
  this.tours = {
    'grandTour'           : this.WELCOMETOUR,
    'infoReminderTour'    : this.INFOREMINDER
  };

  this.currActiveTour = "";
  this.tourActive = false;

  var self = this;

  this.init = function(callback) {
    //console.log("HelpTours >> f:init >> self: " + self);
    $(document).on(this.TOURFINISHED, this.tourEnded);

    grandTour = new GrandTour(this.WELCOMETOUR);
    infoReminderTour = new InfoReminderTour(this.INFOREMINDER);

//    this.tours["grandTour"] = self.WELCOMETOUR;
//    this.tours["infoReminderTour "]= self.INFOREMINDER;
    //console.log("HelpTours >> f:init >> this.tours: " , this.tours);

    if (callback != undefined) callback();
  };


  this.startTour = function(which, scope) {
    if (scope == undefined) scope = this;
//    console.log("HelpTours >> f:startTour >> scope: " , scope);
//    console.log("HelpTours >> f:startTour >> currActiveTour: " , scope.currActiveTour.name);
//    console.log("HelpTours >> f:startTour >> currActiveTour.active: " , scope.currActiveTour.active);
//    console.log("HelpTours >> f:startTour >> target to start: '" + which);


    switch (which) {
      case scope.WELCOMETOUR:
        // do welcometour
        //console.log("HelpTours >> f:startTour >> case this.WELCOMETOUR >> scope.tourActive = " + scope.tourActive);
        //console.log("HelpTours >> f:startTour >> case this.WELCOMETOUR");
        if (scope.tourActive) {
          if (scope.currActiveTour.active == true) {
            $(window).joyride('end');
            scope.currActiveTour = undefined;
          }
          scope.tourActive = false;
        }
        $(window).joyride('destroy');
//        var self = this;
          grandTour.init();
        setTimeout(function(scp) {
          grandTour.start();
          scp.currActiveTour = grandTour;
          scp.tourActive = true;
        }, 250, scope);
//        $(window).joyride('restart');

        break;
      case self.INFOREMINDER:
        // do info reminder
//      console.log("HelpTours >> f:startTour >> case self.INFOREMINDER >> scope.tourActive = " + scope.tourActive);
        //console.log("HelpTours >> f:startTour >> case self.INFOREMINDER");
        if (scope.tourActive) {
//          console.log("    killing previous joyride... ");
          if (scope.currActiveTour.active == true) {
            $(window).joyride('end');
            scope.currActiveTour = undefined;
          }
//          console.log("    setting tourActive to false....");
          scope.tourActive = false;
//          console.log("    scope.tourActive: " + scope.tourActive);
        }
        $(window).joyride('destroy');
//        var self = this;
          infoReminderTour.init();
        setTimeout(function(scp) {
          infoReminderTour.start();
          scp.currActiveTour = infoReminderTour;
          scp.tourActive = true;
        }, 250, scope);

        break;
    }
  }

  this.tourEnded = function(e, n) {
    //console.log("HelpTours >> f:tourEnded >> self.tourActive: " + self.tourActive + ", name: " + n);

    $(window).joyride('destroy');
    self.currActiveTour = undefined;
    self.tourActive = false;

    message.hide();
    printer.checkStatus();
  }
}

var keyboardShortcutsEnabled = true;
var keyboardEscapeEnterEnabled = false;
var wordBuffer = "";

var wordFuncs = {
		"idbeholdl": function() {
			alert("Light!");
		},
		"idspispopd": function() {
			drawTextOnCanvas("Im in ur kanvas drawin' ur stuffz.");
		},
		"dia": function() {
			var cx = canvasWidth / 2;
			var cy = canvasHeight /2;
			drawCircle(cx, cy, 50, 4);
			shapeMoveTo(cx - 20, cy);
			shapeLineTo(cx + 20, cy);
			shapeMoveTo(cx, cy - 20);
			shapeLineTo(cx, cy + 20);
		},
		"stats": function() {
			var text = "Shape statistics:\nNumber of points: " + _points.length;
			alert(text);
		},
		"pdump": function() {
			console.log("points array: " + _points);
		}
};

function initKeyboard() {

	$(document).keypress(function(event) {

		if (keyboardEscapeEnterEnabled) {
			switch (event.keyCode) {
			case 13:
				$(document).trigger("onEnterKey");
				break;
			case 27:
				$(document).trigger("onEscapeKey");
				break;
			}
		}

		if (!keyboardShortcutsEnabled) return;
		if (event.ctrlKey && event.altKey && ! event.metaKey) processWords(event);
		if (event.altKey || event.ctrlKey || event.metaKey) return; //ignore key presses with modifier keys except shift

		var ch = String.fromCharCode(event.which);

		switch (ch) {
			case '+': case '=': zoomShape(1.05); break;
			case ',': openSettingsWindow(); break;
			case '-': zoomShape(.95); break;
			case ';': moveShape(-5,0); break;
			case '[': previewTwistLeft(); break;
			case '\'': moveShape(5,0); break;
			case ']': previewTwistRight(); break;
			case 'c': newSketch(); break;
			case 'f': showTravelLines=!showTravelLines; redrawDoodle(); break;
			case 'g': settingsWindow.downloadGcode(); break;
			case 'H': previewDown(true); break;
			case 'h': previewUp(true); break;
			case 'i': showShapeDialog(); break;
			case 'L': nextSketch(); break;
			case 'l': prevSketch(); break;
			case 'n': newSketch(); break;
			case 'p': print(); break;
			case 'q': stopPrint(); break;
			case 'R': rotateShape(-.1); break;
			case 'r': rotateShape(.1); break;
			case 's': saveSketch(); break;
			case 'T': showScanDialog(); break;
			case 't': showWordArtDialog(); break;
			case 'u': oopsUndo(); break;
			case '|': resetTwist(); break;
			
			//default: console.log("Key: '" + ch + "' (" + event.which + ")");
		}
		if(event.which != 13) { // don't prevent enter usage, it's used in tour
			event.preventDefault(); //prevents the character to end up in a focussed textfield
		}
	})

}

function processWords(e) {
	wordBuffer += String.fromCharCode(e.which);
	
	var match = false;
	for (var k in wordFuncs) {
		if (k.indexOf(wordBuffer) == 0) {
			if (k.length == wordBuffer.length) match = wordFuncs[k];
			else match = true;
			break;
		}
	}
	
	if (typeof(match) == 'function') {
		match();
		wordBuffer = "";
	} else if (!match) {
		wordBuffer = "";
	}
}

/*
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
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

/* not using this now
var $printProgressContainer = $("#printProgressContainer");
var $progressbar = $("#progressbar");
var $progressAmount = $(".progressAmount");
function setPrintprogress(val) {
	if (isNaN(val)) return;
//	console.log("f:setPrintprogress() >> val " + val);
	$progressbar.css("width", val*100 + "%");
	$progressAmount.text(Math.floor(val*100) + "%");
}
//*/

function Printer() {
	var className = 'Printer';

	Printer.WIFIBOX_DISCONNECTED_STATE	= "wifibox disconnected";
	Printer.UNKNOWN_STATE				= "unknown";				// happens when a printer is connection but there isn't communication yet
	Printer.DISCONNECTED_STATE			= "disconnected";			// printer disconnected
	Printer.CONNECTING_STATE 			= "connecting";				// printer connecting (printer found, but driver has not yet finished setting up the connection)
	Printer.IDLE_STATE 					= "idle"; 					// printer found and ready to use, but idle
	Printer.BUFFERING_STATE				= "buffering";				// printer is buffering (recieving) data, but not yet printing
	Printer.PRINTING_STATE				= "printing";
	Printer.STOPPING_STATE				= "stopping";				// when you stop (abort) a print it prints the endcode
	Printer.TOUR_STATE					= "tour";					// when in joyride mode

	Printer.ON_BEFORE_UNLOAD_MESSAGE = "You're doodle is still being sent to the printer, leaving will result in a incomplete 3D print";

	this.temperature 		= 0;
	this.targetTemperature 	= 0;
	this.currentLine 		= 0;
	this.totalLines			= 0;
	this.bufferedLines		= 0;
	this.state				= Printer.UNKNOWN_STATE;
	this.hasControl			= true;	// whether this client has control access

	this.wifiboxURL;

	this.checkStatusInterval = 3000;
	this.checkStatusDelay;
	this.timeoutTime = 3000;
	this.sendPrintPartTimeoutTime = 5000;

	this.gcode; 							// gcode to be printed
	this.sendLength = 500; 					// max amount of gcode lines per post (limited because WiFi box can't handle too much)

	this.retryDelay = 2000; 				// retry setTimout delay
	this.retrySendPrintPartDelay; 			// retry setTimout instance
	this.retryCheckStatusDelay; 			// retry setTimout instance
	this.retryStopDelay;					// retry setTimout instance
	this.retryPreheatDelay;					// retry setTimout instance

	Printer.MAX_GCODE_SIZE = 10;			// max size of gcode in MB's (estimation)

	this.stateOverruled = false;

	// Events
	Printer.UPDATE = "update";

	var self = this;

	this.init = function() {
		//console.log("Printer:init");
		//this.wifiboxURL = "http://" + window.location.host + "/cgi-bin/d3dapi";
		//this.wifiboxURL = "http://10.10.0.1/cgi-bin/d3dapi";
		this.wifiboxURL = wifiboxURL;
		//this.wifiboxURL = "proxy5.php";
		//console.log("  wifiboxURL: ",this.wifiboxURL);

		if (autoUpdate) {
			this.startStatusCheckInterval();
		}
	}

	this.preheat = function() {
		console.log("Printer:preheat");

		if (this.state != Printer.IDLE_STATE) return;

		var self = this;
		if (communicateWithWifibox) {
			$.ajax({
				url: this.wifiboxURL + "/printer/heatup",
				type: "POST",
				dataType: 'json',
				timeout: this.timeoutTime,
				success: function(data){
					console.log("Printer:preheat response: ",data);
					if(data.status != "success") {
						clearTimeout(self.retryPreheatDelay);
						self.retryPreheatDelay = setTimeout(function() { self.preheat() },self.retryDelay); // retry after delay
					}
				}
			}).fail(function() {
				console.log("Printer:preheat: failed");
				clearTimeout(self.retryPreheatDelay);
				self.retryPreheatDelay = setTimeout(function() { self.preheat() },self.retryDelay); // retry after delay
			});
		} else {
			console.log ("Printer >> f:preheat() >> communicateWithWifibox is false, so not executing this function");
		}
	}

	this.print = function(gcode) {
		console.log("Printer:print");
		console.log("  gcode total # of lines: " + gcode.length);

		message.set("Sending doodle to printer...",Message.NOTICE);
		self.addLeaveWarning();

		/*for (i = 0; i < gcode.length; i++) {
			gcode[i] += " (" + i + ")";
		}*/

		this.sendIndex = 0;
		this.gcode = gcode;

		//console.log("  gcode[20]: ",gcode[20]);
		var gcodeLineSize = this.byteSize(gcode[20]);
		//console.log("  gcodeLineSize: ",gcodeLineSize);
		var gcodeSize = gcodeLineSize*gcode.length/1024/1024; // estimate gcode size in MB's
		console.log("  gcodeSize: ",gcodeSize);

		if(gcodeSize > Printer.MAX_GCODE_SIZE) {
			var msg = "Error: Printer:print: gcode file is probably too big ("+gcodeSize+"MB) (max: "+Printer.MAX_GCODE_SIZE+"MB)";
			alert(msg);
			console.log(msg);

			this.overruleState(Printer.IDLE_STATE);
			this.startStatusCheckInterval();
			message.hide();
			self.removeLeaveWarning();

			return;
		}

		//this.targetTemperature = settings["printer.temperature"]; // slight hack

		this.sendPrintPart(this.sendIndex, this.sendLength);
	}

	this.byteSize = function(s){
		return~-encodeURI(s).split(/%..|./).length;
	}

	this.sendPrintPart = function(sendIndex,sendLength) {
		console.log("Printer:sendPrintPart sendIndex: " + sendIndex + "/" + this.gcode.length + ", sendLength: " + sendLength);


		var sendPercentage = Math.round(sendIndex/this.gcode.length*100);
		message.set("Sending doodle to printer: "+sendPercentage+"%",Message.NOTICE,false,true);

		var firstOne = (sendIndex == 0)? true : false;
		var start = firstOne; // start printing right away

		var completed = false;
		if (this.gcode.length < (sendIndex + sendLength)) {
			console.log("  sending less than max sendLength (and last)");
			sendLength = this.gcode.length - sendIndex;
			//lastOne = true;
			completed = true;
		}
		var gcodePart = this.gcode.slice(sendIndex, sendIndex+sendLength);

		var postData = { gcode: gcodePart.join("\n"), first: firstOne, start: start};
		var self = this;
		if (communicateWithWifibox) {
			$.ajax({
				url: this.wifiboxURL + "/printer/print",
				type: "POST",
				data: postData,
				dataType: 'json',
				timeout: this.sendPrintPartTimeoutTime,
				success: function(data){
					console.log("Printer:sendPrintPart response: ",data);

					if(data.status == "success") {
						if (completed) {
							console.log("Printer:sendPrintPart:gcode sending completed");
							this.gcode = [];
							//btnStop.css("display","block"); // hack
							btnStop.enable(); //check me
							self.removeLeaveWarning();
							message.set("Doodle has been sent to printer...",Message.INFO,true);
							//self.targetTemperature = settings["printer.temperature"]; // slight hack
						} else {
							// only if the state hasn't been changed (by for example pressing stop) we send more gcode

							//console.log("Printer:sendPrintPart:gcode part received (state: ",self.state,")");
							if(self.state == Printer.PRINTING_STATE || self.state == Printer.BUFFERING_STATE) {
								//console.log("Printer:sendPrintPart:sending next part");
								self.sendPrintPart(sendIndex + sendLength, sendLength);
							}
						}
					}
					// after we know the first gcode packed has bin received or failed
					// (and the driver had time to update the printer.state)
					// we start checking the status again
					if(sendIndex == 0) {
						self.startStatusCheckInterval();
					}
				}
			}).fail(function() {
				console.log("Printer:sendPrintPart: failed");
				clearTimeout(self.retrySendPrintPartDelay);
				self.retrySendPrintPartDelay = setTimeout(function() {
					console.log("request printer:sendPrintPart failed retry");
					self.sendPrintPart(sendIndex, sendLength)
				},self.retryDelay); // retry after delay

				// after we know the gcode packed has bin received or failed
				// (and the driver had time to update the printer.state)
				// we start checking the status again
				self.startStatusCheckInterval();
			});
		} else {
			console.log ("Printer >> f:sendPrintPart() >> communicateWithWifibox is false, so not executing this function");
		}
	}

	this.stop = function() {
		var endCode = generateEndCode();
		var postData = { gcode: endCode.join("\n")};
		var self = this;
		if (communicateWithWifibox) {
			$.ajax({
				url: this.wifiboxURL + "/printer/stop",
				type: "POST",
				data: postData,
				dataType: 'json',
				timeout: this.timeoutTime,
				success: function(data){
					console.log("Printer:stop response: ", data);

					// after we know the stop has bin received or failed
					// (and the driver had time to update the printer.state)
					// we start checking the status again
					self.startStatusCheckInterval();
				}
			}).fail(function() {
				console.log("Printer:stop: failed");
				clearTimeout(self.retryStopDelay);
				self.retryStopDelay = setTimeout(function() { self.stop() },self.retryDelay); // retry after delay

				// after we know the stop has bin received or failed
				// (and the driver had time to update the printer.state)
				// we start checking the status again
				self.startStatusCheckInterval();
			});
		} else {
			console.log ("Printer >> f:stop() >> communicateWithWifibox is false, so not executing this function");
		}
	}

	this.startStatusCheckInterval = function() {
		console.log("Printer:startStatusCheckInterval");
		self.checkStatus();
		clearTimeout(self.checkStatusDelay);
		clearTimeout(self.retryCheckStatusDelay);
		self.checkStatusDelay = setTimeout(function() { self.checkStatus() }, self.checkStatusInterval);
	}

	this.stopStatusCheckInterval = function() {
		console.log("Printer:stopStatusCheckInterval");
		clearTimeout(self.checkStatusDelay);
		clearTimeout(self.retryCheckStatusDelay);
	}

	this.checkStatus = function() {
		return;
		if (limitedFeatures) {
			console.log(className,'ignoring checkStatus due to limitedFeatures mode');
			return; //don't check printer status when in limitedFeatures mode
		}

		//console.log("Printer:checkStatus");
		this.stateOverruled = false;
		//console.log("  stateOverruled: ",this.stateOverruled);
		var self = this;
		if (communicateWithWifibox) {
			$.ajax({
				url: this.wifiboxURL + "/info/status",
				dataType: 'json',
				timeout: this.timeoutTime,
				success: function(response){
					//console.log("  Printer:status: ",response.data.state); //," response: ",response);

					self.handleStatusUpdate(response);

					clearTimeout(self.checkStatusDelay);
					clearTimeout(self.retryCheckStatusDelay);
					self.checkStatusDelay = setTimeout(function() { self.checkStatus() }, self.checkStatusInterval);
				}
			}).fail(function() {
				console.log("Printer:checkStatus: failed");
				self.state = Printer.WIFIBOX_DISCONNECTED_STATE;
				clearTimeout(self.checkStatusDelay);
				clearTimeout(self.retryCheckStatusDelay);
				self.retryCheckStatusDelay = setTimeout(function() { self.checkStatus() },self.retryDelay); // retry after delay
				$(document).trigger(Printer.UPDATE);
			});
		} else {
			console.log ("Printer >> f:checkStatus() >> communicateWithWifibox is false, so not executing this function");
		}
	}

	this.handleStatusUpdate = function(response) {
		//console.log("Printer:handleStatusUpdate response: ",response);
		var data = response.data;
		if(response.status != "success") {
			self.state = Printer.UNKNOWN_STATE;
		} else {
			// state
			//console.log("  stateOverruled: ",this.stateOverruled);
			if(!this.stateOverruled) {
				self.state = data.state;
				//console.log("  state > ",self.state);
			}

			// temperature
			self.temperature = data.hotend;
			self.targetTemperature = data.hotend_target;

			// progress
			self.currentLine = data.current_line;
			self.totalLines = data.total_lines;
			self.bufferedLines = data.buffered_lines

			// access
			self.hasControl = data.has_control;

			if(self.state == Printer.PRINTING_STATE || self.state == Printer.STOPPING_STATE) {
				console.log("progress: ",self.currentLine+"/"+self.totalLines+" ("+self.bufferedLines+") ("+self.state+")");
			}
		}
		$(document).trigger(Printer.UPDATE);
	}

	this.overruleState = function(newState) {
		this.stateOverruled = true;
		console.log("  stateOverruled: ",this.stateOverruled);

		self.state = newState;

		$(document).trigger(Printer.UPDATE);

		this.stopStatusCheckInterval();
	}

	this.removeLeaveWarning = function() {
		window.onbeforeunload = null;
	}

	this.addLeaveWarning = function() {
		window.onbeforeunload = function() {
			console.log("WARNING:"+Printer.ON_BEFORE_UNLOAD_MESSAGE);
			return Printer.ON_BEFORE_UNLOAD_MESSAGE;
		};
	}
}

// JavaScript Document

function changeCapsule() {
	alert("changeCapsule");
}

function printerHome() {
	
	$.post( "http://10.10.0.1:5000/api/printer/print", { gcode: "G90; G0 X0Y0Z0", start: "true", first: "true" } )
  		.done(function( data ) {
			if (data.status == "error")	alert( "Error-Message: " + data.msg );
  		});
		
}

function printerXUp() {
	
	$.post( "http://10.10.0.1:5000/api/printer/print", { gcode: "G91; G0 X1", start: "true", first: "true" } )
  		.done(function( data ) {
			if (data.status == "error")	alert( "Error-Message: " + data.msg );
  		});

}

function printerXDown() {
	
	$.post( "http://10.10.0.1:5000/api/printer/print", { gcode: "G91; G0 X-1", start: "true", first: "true" } )
  		.done(function( data ) {
			if (data.status == "error")	alert( "Error-Message: " + data.msg );
  		});

}

function printerYUp() {
	
	$.post( "http://10.10.0.1:5000/api/printer/print", { gcode: "G91; G0 Y1", start: "true", first: "true" } )
  		.done(function( data ) {
			if (data.status == "error")	alert( "Error-Message: " + data.msg );
  		});

}

function printerYDown() {
	
	$.post( "http://10.10.0.1:5000/api/printer/print", { gcode: "G91; G0 Y-1", start: "true", first: "true" } )
  		.done(function( data ) {
			if (data.status == "error")	alert( "Error-Message: " + data.msg );
  		});

}

function printerZUp() {
	
	$.post( "http://10.10.0.1:5000/api/printer/print", { gcode: "G91; G0 Z1", start: "true", first: "true" } )
  		.done(function( data ) {
			if (data.status == "error")	alert( "Error-Message: " + data.msg );
  		});

}

function printerZDown() {
	
	$.post( "http://10.10.0.1:5000/api/printer/print", { gcode: "G91; G0 Z-1", start: "true", first: "true" } )
  		.done(function( data ) {
			if (data.status == "error")	alert( "Error-Message: " + data.msg );
  		});

}


/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

function Progressbar() {
  this.currProgress = 0; // default val

  this.progressbarFGImg = new Image();
  this.progressbarFGImgSrc = "/plugin/bocusini_doodler/static/img/progress_fg.png";
  this.progressbarBGImg = new Image();
  this.progressbarBGImgSrc = "/plugin/bocusini_doodler/static/img/progress_bg.png";

  this.progressWidth= 93;
  this.progressHeight = 82;

  this.quartPI = .5 * Math.PI;
  this.twoPI = 2 * Math.PI;

  // To make the progressbar start with a minimal amount of 'progress'
  // so that you can visually see that there is progress
  this.progressPadding = Math.PI * .1;

  this.$canvas;
  this.canvas;
  this.context;
  this.$container;

  this.isInitted = false;

  this.enabled = true;

  this.init = function(targCanvas, targCanvasContainer) {
    console.log("Thermometer.init()");

    this.$container = targCanvasContainer;

    this.$canvas = targCanvas;
    this.canvas = this.$canvas[0];
    this.context = this.canvas.getContext('2d');


    var self = this;
    this.progressbarBGImg.onload = function() {
      //console.log("progressbarBGImg img loaded");
      //        self.isInitted = true;
      //        self.update(self.currentTemperature, self.targetTemperature);

      self.progressbarFGImg.onload = function() {
        console.log("progressbarFGImg img loaded");
        self.isInitted = true;
        self.update(0, 100);
      };
      self.progressbarFGImg.src = self.progressbarFGImgSrc;
    };
    this.progressbarBGImg.src = this.progressbarBGImgSrc;
  }

  this.update = function(part, total) {
    //console.log("Progressbar.update(" + part + "," + total + ")");

    var pct = part / total;
    if (this.isInitted) {
      if (part == undefined) part = 0;
      if (total== undefined) total = 100; // prevent divide by zero

      var progress = part / total;
      progress = Math.min(progress, 1.0);
      progress = Math.max(progress, 0);
      //console.log("progressbar >> f:update() >> progress: " + progress);

      // clear
      this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);

      this.context.drawImage(this.progressbarBGImg, 0, 0);

      this.context.font = "7pt sans-serif";

      // draw the progressbar foreground's clipping path
      this.context.save();
      this.context.beginPath();
      this.context.moveTo(45, 45);
      this.context.lineTo(45, 0);
      this.context.arc(45, 45, 45, -this.quartPI, -this.quartPI + this.progressPadding + (progress * (this.twoPI - this.progressPadding)), false); // circle bottom of thermometer
      this.context.lineTo(45, 45);
      this.context.clip();

      this.context.drawImage(this.progressbarFGImg, 0, 0);
      this.context.restore();

      if (debugMode) {
        this.context.fillStyle = '#222';
        this.context.strokeStyle = '#fff';
        this.context.lineWidth = 3;
        this.context.textAlign="center";
        this.context.strokeText(part + " / " + total, 45, 45, 90);
        this.context.fillText(part + " / " + total, 45, 45, 90);
      }

    } else {
      console.log("Progressbar.setTemperature() -> thermometer not initialized!");
    }
  }
  this.show = function() {
    this.$container.addClass("progressbarAppear");
    //  	this.$container.show();
    this.enabled = true;
  }
  this.hide = function() {
    this.$container.removeClass("progressbarAppear");
    //  	this.$container.hide();
      this.enabled = false;
  }
}

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
  setSketchModified(true);
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
  setSketchModified(true);
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
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

//SVG validator: http://validator.w3.org/
//SVG viewer: http://svg-edit.googlecode.com/svn/branches/2.6/editor/svg-editor.html
function saveToSvg() {
	var lastX = 0, lastY = 0, lastIsMove = false;
	var svg = '';

	var boundsWidth = doodleBounds[2] - doodleBounds[0];
	var boundsHeight = doodleBounds[3] - doodleBounds[1];

	svg += '<?xml version="1.0" standalone="no"?>\n';
	svg += '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n';
	svg += '<svg width="' + boundsWidth + '" height="' + boundsHeight + '" version="1.1" xmlns="http://www.w3.org/2000/svg">\n';
	svg += '\t<desc>Doodle 3D sketch</desc>\n';

	var data = '';
	for (var i = 0; i < _points.length; ++i) {
		var x = _points[i][0], y = _points[i][1], isMove = _points[i][2];
		var dx = x - lastX, dy = y - lastY;

		if (i == 0)
			data += 'M'; //emit absolute move on first pair of coordinates
		else if (isMove != lastIsMove)
			data += isMove ? 'm' : 'l';

		data += dx + ',' + dy + ' ';

		lastX = x;
		lastY = y;
		lastIsMove = isMove;
	}

	svg += '\t<path transform="translate(' + -doodleBounds[0] + ',' + -doodleBounds[1] + ')" d="' + data + '" fill="none" stroke="black" stroke-width="2" />\n';

	var fields = JSON.stringify({'height': numLayers, 'outlineShape': VERTICALSHAPE, 'twist': rStep});
	svg += '\t<!--<![CDATA[d3d-keys ' + fields + ']]>-->\n';

	svg += '</svg>\n';

	return svg;
}


//TODO: use local variables instead of _points,numLayers,VERTICALSHAPE and rStep so we can leave a current doodle in tact if an error occurs while parsing
function loadFromSvg(svgData) {
	var mode = '', x = 0, y = 0;

	console.log("loading " + svgData.length + " bytes of data...");

	clearDoodle();

	svgData = svgData.replace("M0,0 ",""); //RC: hack

	var p = svgData.indexOf("<path");
	if (p == -1) { console.log("loadFromSvg: could not find parsing start point"); return false; }
	p = svgData.indexOf('d="', p);
	if (p == -1) { console.log("loadFromSvg: could not find parsing start point"); return false; }
	p += 3; //skip 'd="'

	var skipSpace = function() { while (svgData.charAt(p) == ' ') p++; }
	var parseCommand = function() {
		while (true) {
			skipSpace();
			var c = svgData.charAt(p);
			if (c == 'M' || c == 'm' || c == 'L' || c == 'l') { //new command letter
				mode = c;
			} else if (c == '"') { //end of command chain
				return true;
			} else { //something else, must be a pair of coordinates...
				var tx = 0, ty = 0, numberEnd = 0, len = 0;
				// var firstComma = svgData.indexOf(',', p);
				// var firstSpace = svgData.indexOf(' ', p);

				numberEnd = svgData.indexOf(',', p);

				////// RC: if instead of a comma a space is used between a pair use that as a separator
				var firstSpace = svgData.indexOf(' ', p);
				if (firstSpace<numberEnd) numberEnd=firstSpace;   
				//console.log('numberEnd',numberEnd,firstSpace);
				////////////////

				if (numberEnd == -1) { console.log("could not find comma in coordinate pair"); return false; }
				len = numberEnd - p;
				tx = parseFloat(svgData.substr(p, len));
				p += len + 1;
				skipSpace();
				numberEnd = svgData.indexOf(' ', p);
				if (numberEnd == -1) { console.log("could not find space after coordinate pair"); return false; }
				len = numberEnd - p;
				ty = parseFloat(svgData.substr(p, len));
				p += len;

				if (mode == 'M' || mode == 'L') {
					x = tx; y = ty;
				} else if (mode == 'm' || mode == 'l') {
					x += tx; y += ty;
				} else {
					console.log("loadFromSvg: found coordinate pair but mode was never set");
					return false;
				}

				var isMove = mode == 'm' || mode == 'M';

				//TODO: create script-wide function for adding points?
				//console.log("inserting "+x+","+y+" ",isMove);
				updatePrevX = x;
				updatePrevY = y;
				_points.push([x, y, isMove]);
				adjustBounds(x, y);
				adjustPreviewTransformation();

				if (isMove) draw(x, y, .5);
				else draw(x, y);
			}
			p++;
		}

		return true;
	};

	parseCommand(); //depends on value of p, so don't move this without taking that into consideration

	const fieldDefMarker = "<!--<![CDATA[d3d-keys";
	p = svgData.indexOf(fieldDefMarker);
	if (p == -1) { console.log("loadFromSvg: could not find metadata marker"); return false; }
	p += fieldDefMarker.length;
	skipSpace();

	var endP = svgData.indexOf("]]>-->", p);
	if (endP == -1) { console.log("loadFromSvg: could not find metadata end-marker"); return false; }
	var metaFields = JSON.parse(svgData.substr(p, endP - p));
	//TODO: log error and return false if parsing failed
	for (var k in metaFields) {
		var v = metaFields[k];
		switch (k) {
		case "height": numLayers = v; break;
		case "outlineShape": VERTICALSHAPE = v; break;
		case "twist": rStep = v; break;
		}
	}

	renderToImageDataPreview();

	return true;
}

/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

// TODO assess if this var is still necessary
var $displayThermometer = $("#thermometerContainer");


//TODO 2013-09-18 allow displaying temperatures HIGHER than the targTemp (it's now being capped at targTemp).
function Thermometer() {
  this.currentTemperature = 0; // default val
  this.targetTemperature = 0; // default val

  this.thermoOverlayImg = new Image();
  this.thermoOverlayImgSrc = "/plugin/bocusini_doodler/static/img/thermometer_fg_overlay.png"; // ../img/thermometer_fg_overlay.png

  this.thermoWidth= 40;
  this.thermoHeight = 100;

  this.$canvas;
  this.canvas;
  this.context;
  this.$container;
  
  this.isInitted = false;
  
  this.enabled = true;
  
  this.thermoColors = [
    [50, 200, 244], // 'cold'
    [244, 190, 10], // 'warming up'
    [244, 50, 50]   // 'ready / hot'
  ];

  this.init = function(targCanvas, targCanvasContainer) {
    //console.log("Thermometer.init()");

    this.$container = targCanvasContainer;

    this.$canvas = targCanvas;
    this.canvas = this.$canvas[0];
    this.context = this.canvas.getContext('2d');


    var self = this;
    this.thermoOverlayImg.onload = function() {
      //console.log("canvasThermoOverlay img loaded");
      self.isInitted = true;
      self.update(self.currentTemperature, self.targetTemperature);
    };
    this.thermoOverlayImg.src = this.thermoOverlayImgSrc;
  }

  this.update = function(curr, targ) {
    //      console.log("Thermometer.update(" + curr + "," + targ + ")");

    if (this.isInitted) {
    	if(!this.enabled) return;
      if (curr == undefined) curr = 0;
      if (targ== undefined) targ = 180; // prevent divide by zero

      var progress = curr / targ;

//      progress = Math.min(progress, 1.0);
      progress = Math.max(progress, 0);

      var h = this.thermoHeight; // 94 // px
      var paddingUnder = 15; // how far is beginpoint from bottom of thermometer
      var paddingAbove = 25; // how far is endpoint from top of thermometer
      var endPoint = h * .8;
      var p = Math.floor((h - paddingUnder - paddingAbove) * progress); // %
      //    var tempHeight =

      var currColor = this.thermoColors[0];
      if (progress > 0.98) {
        currColor = this.thermoColors[2];
      } else if (progress > 0.25) {
        currColor = this.thermoColors[1];
      }

      // clear
      this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.context.font = "10pt sans-serif";

      // draw the thermometer clipping path
      this.context.save();
      this.context.beginPath();
      this.context.arc(40, 80, 16, 0, 2 * Math.PI, false); // circle bottom of thermometer
      this.context.arc(40, 10, 4, 0, 2 * Math.PI, false); // circle at top of thermometer tube
      this.context.rect(36, 11, 8, 70); // thermometer tube
      this.context.fillStyle = '#fff';
      this.context.fill();
      this.context.clip();

      // draw rectangle which represents temperature
      // rect will be clipped by the thermometer outlines
      this.context.beginPath();
      this.context.rect(20, h - paddingUnder - p, 60, p + paddingUnder);
      //console.log("   currColor: " + currColor);
      //todo Math.floor??
      this.context.fillStyle = "rgb(" + currColor[0] + "," + currColor[1] + "," + currColor[2] + ")";
      this.context.fill();
      this.context.restore();

      // additional text labels
      this.context.save();
      this.context.beginPath();
      this.context.moveTo(32, paddingAbove);
      this.context.lineTo(52, paddingAbove);
      this.context.lineWidth = 2;
      this.context.strokeStyle = '#000';
      this.context.stroke();
      this.context.fillStyle = '#000';
      this.context.textAlign = "left";
      this.context.textBaseline = "middle";
      this.context.fillText(targ + "°", 55, paddingAbove);
      this.context.restore();

      // the thermometer outline png
      this.context.drawImage(this.thermoOverlayImg, 20, 0);

      // text
      this.context.fillStyle = '#000';
      this.context.textAlign="center";
      this.context.fillText(curr + "°", 40, h + paddingUnder);
    } else {
      console.log("Thermometer.setTemperature() -> thermometer not initialized!");
    }
  }
  this.show = function() {
    this.$container.addClass("thermometerAppear");
//    $("#progressbarCanvasContainer").addClass("thermometerAppear");
//  	this.$container.show();
  	this.enabled = true;
  }
  this.hide = function() {
    this.$container.removeClass("thermometerAppear");
//    $("#progressbarCanvasContainer").removeClass("thermometerAppear");
//  	this.$container.hide();
  	this.enabled = false;
  }
}

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
	
	btnPDHome = new Button("#btnPDHome");
	btnPDX = new Button("#btnPDX");
	btnPDY = new Button("#btnPDY");
	btnPDZ = new Button("#btnPDZ");
	btnPDC = new Button("#btnPDC");
	

	$(".btn").Button(); //initalize other buttons

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
	btnSave.on("onButtonClick", saveSketch);
	btnPrevious.on("onButtonClick", previousSketch);
	btnNext.on("onButtonClick", nextSketch);
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
	
	btnPDHome.on("onButtonClick", onbtnPDHome);
	btnPDX.on("onButtonHold", onBtnPDX);
	btnPDY.on("onButtonHold", onBtnPDY);
	btnPDZ.on("onButtonHold", onBtnPDZ);
	btnPDC.on("onButtonClick", changeCapsule);
	
	btnFileManager.on("onButtonClick", onBtnFileManager);
	//btnOctoPrint.on("onButtonClick", onBtnOctoPrint);
	btnShutdown.on("onButtonClick", onBtnShutdown);

	//getSavedSketchStatus();
	listSketches();
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
	
	function onbtnPDHome(e) {
		printerHome();
	}

	function onBtnPDX(e,cursor) {
		var h = btnPDX.height();
		if(cursor.y < h/2) {
			printerXUp();
		} else {
			printerXDown();
		}
	}

	function onBtnPDY(e,cursor) {
		var h = btnPDY.height();
		if(cursor.y < h/2) {
			printerYUp();
		} else {
			printerYDown();
		}
	}

	function onBtnPDZ(e,cursor) {
		var h = btnPDZ.height();
		if(cursor.y < h/2) {
			printerZUp();
		} else {
			printerZDown();
		}
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
	setSketchModified(true);

//	redrawPreview(redrawLess);
	redrawRenderedPreview(redrawLess);
}
function previewDown(redrawLess) {
	//    console.log("f:previewDown()");
	if (numLayers > minNumLayers) {
		numLayers--;
	}
	setSketchModified(true);
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
	setSketchModified(true);
}

function resetTwist() {
	rStep = 0;
	redrawRenderedPreview();
	setSketchModified(true);
}

function update() {
	setState(printer.state,printer.hasControl);

	thermometer.update(printer.temperature, printer.targetTemperature);
	progressbar.update(printer.currentLine, printer.totalLines);
}

function setState(newState,newHasControl) {
	if(newState == state && newHasControl == hasControl) return;

	prevState = state;

	console.log("setState: ",prevState," > ",newState," ( ",newHasControl,")");
	setDebugText("State: "+newState);

	// print button
	var printEnabled = (newState == Printer.IDLE_STATE && newHasControl);
	if(printEnabled) {
		btnPrint.enable();
		btnPDHome.enable();
		btnPDX.enable();
		btnPDY.enable();
		btnPDZ.enable();
		btnPDC.enable();
	} else {
		//btnPrint.disable();
		//btnPDHome.disable();
		//btnPDX.disable();
		//btnPDY.disable();
		//btnPDZ.disable();
		//btnPDC.disable();
	}

	// stop button
	var stopEnabled = ((newState == Printer.PRINTING_STATE || newState == Printer.BUFFERING_STATE) && newHasControl);
	if(stopEnabled) {
		btnStop.enable();
	} else {
		btnStop.disable();
	}

	// thermometer
	switch(newState) {
	case Printer.IDLE_STATE: /* fall-through */
	case Printer.BUFFERING_STATE: /* fall-through */
	case Printer.PRINTING_STATE: /* fall-through */
	case Printer.STOPPING_STATE:
		thermometer.show();
		break;
	default:
		thermometer.hide();
	break;
	}

	// progress indicator
	switch(newState) {
	case Printer.PRINTING_STATE:
		progressbar.show();
		break;
	default:
		progressbar.hide();
	break;
	}

	/* settings button */
	switch(newState) {
	case Printer.CONNECTING_STATE: /* fall-through */
	case Printer.IDLE_STATE:
		btnSettings.enable();
		break;
	case Printer.WIFIBOX_DISCONNECTED_STATE: /* fall-through */
	case Printer.BUFFERING_STATE: /* fall-through */
	case Printer.PRINTING_STATE: /* fall-through */
	case Printer.STOPPING_STATE:
		//btnSettings.disable();
		break;
	default:
		btnSettings.enable();
	break;
	}

	/* save, next and prev buttons */
	switch(newState) {
	case Printer.WIFIBOX_DISCONNECTED_STATE:
		btnPrevious.disable();
		btnNext.disable()
		btnSave.disable();
		break;
	default:
		// updatePrevNextButtonState();
		updateSketchButtonStates();
		if (isModified) btnSave.enable();
	break;
	}

	if(connectingHintDelay && newState != Printer.CONNECTING_STATE) {
		clearTimeout(connectingHintDelay);
		connectingHintDelay = null;
	}

	if(newState == Printer.WIFIBOX_DISCONNECTED_STATE) {
		message.set("Lost connection to WiFi box",Message.ERROR);
	}	else if(prevState == Printer.WIFIBOX_DISCONNECTED_STATE) {
		message.set("Connected to WiFi box",Message.INFO,true);
	} else if(newState == Printer.DISCONNECTED_STATE) {
		message.set("Printer disconnected",Message.WARNING,true);
	} else if(newState == Printer.CONNECTING_STATE) {
		message.set("Printer connecting...",Message.INFO,false);
		if (prevState != Printer.CONNECTING_STATE) { //enable 'watchdog' if we entered from a different state
			clearTimeout(connectingHintDelay);
			connectingHintDelay = setTimeout(function() {
				message.set("Printer still not connected, did you<br/>select the correct printer type?", Message.WARNING, false);
				connectingHintDelay = null;
			}, connectingHintDelayTime);
		}
	} else if(prevState == Printer.DISCONNECTED_STATE && newState == Printer.IDLE_STATE ||
			prevState == Printer.UNKNOWN_STATE && newState == Printer.IDLE_STATE ||
			prevState == Printer.CONNECTING_STATE && newState == Printer.IDLE_STATE) {
		message.set("Printer connected",Message.INFO,true);
		console.log("  preheat: ",settings["printer.heatup.enabled"]);
		if(settings["printer.heatup.enabled"]) {
			// HACK: we delay the preheat because the makerbot driver needs time to connect
			clearTimeout(preheatDelay);
			preheatDelay = setTimeout(printer.preheat,preheatDelayTime); // retry after delay
		}
	}	else if(prevState == Printer.PRINTING_STATE && newState == Printer.STOPPING_STATE) {
		console.log("stopmsg show");
		message.set("Printer stopping",Message.INFO,false);
	}	else if(prevState == Printer.STOPPING_STATE && newState == Printer.IDLE_STATE) {
		console.log("stopmsg hide");
		message.hide();
	}

	state = newState;
	hasControl = newHasControl;
}

/*
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

  setSketchModified(false);
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
    setSketchModified(true);

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

  setSketchModified(true);

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
  setSketchModified(true);

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
  setSketchModified(true);

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
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

function setTemperature(callback) {

  if (callback != undefined) callback();

}
function setTemperature(callback) {

  if (callback != undefined) callback();

}

/*
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
  numLayers: 1, //was 10
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
//*/

// JavaScript Document



function openFileManager() {
		//alert("FileManager");
		location.href = "filemanager/"+location.search;
}
/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

var sidebarLeft;
var sidebarRight;

function initSidebars() {
  console.log("f:initSidebars()");

  sidebarLeft = new SideBar();
  sidebarLeft.init("#leftpanel", "hideleft", function() {
    $("#leftpanel").show();
  });

  sidebarRight = new SideBar();
  sidebarRight.init("#rightpanel", "hideright", function() {
    $("#rightpanel").show();
  });
}

function SideBar() {
  this.initted = false;
  this.$contentTarg = undefined;
  this.$sideBtn = undefined;
  this.contentHidden = false;
  this.hideClass = "";

  this.init = function(targ, hideClass, callback) {
    console.log("SideBar >> f:init >> targ: " , $(targ) , ", hideClass: " + hideClass);
    this.$contentTarg = $(targ);
    this.hideClass = hideClass;

    this.$contentTarg.addClass(this.hideClass);
    this.contentHidden = true;

    this.$contentTarg.append("<div class='sidebutton'></div>");
    this.$sideBtn = $(targ +" .sidebutton");
    var self = this;

    this.$sideBtn.on('click', function(e) {
      console.log("sidebutton");
      self.toggleShowHide();
    });

    this.initted = true;

    callback();
  }

  this.toggleShowHide = function() {
    if (this.contentHidden) {
      this.contentHidden = false;
      this.$contentTarg.removeClass(this.hideClass);
      //        self.$sideBtn.addClass("sidebuttonin");
      this.$sideBtn.addClass("sidebuttonin");
    } else {
      this.contentHidden = true;
      this.$contentTarg.addClass(this.hideClass);
      //        self.$sideBtn.removeClass("sidebuttonin");
      this.$sideBtn.removeClass("sidebuttonin");

    }
  }
}


/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

var curSketch = 0;
var sketches = []; //contains fileIDs
var sketchLoaded = false;

function previousSketch(e) {
	loadSketch(curSketch-1);	
}

function nextSketch(e) {
	loadSketch(curSketch+1);
}

function newSketch(e) {
	clearDoodle();
	curSketch = sketches.length; //index of the last item + 1
	updateSketchButtonStates();
}

function listSketches() {
	console.log('listSketches')
	$.get(wifiboxURL + "/sketch/list", function(data) {
		if (data.status=='success') {
			sketches = data.data.list;
			curSketch = sketches.length-1;
			setSketchModified(false);
			updateSketchButtonStates();

			if (autoLoadSketchId) loadSketch(autoLoadSketchId);
		}
	})
}

function setSketchModified(_isModified) {
	isModified = _isModified;
	updateSketchButtonStates();
}

function updateSketchButtonStates() {
	console.log('sketch: isModified',isModified,'curSketch',curSketch,'sketches.length',sketches.length);

	if (isModified) {
		btnSave.enable();
	}
	else {
		btnSave.disable();
	}

	if (curSketch<sketches.length-1) {
		btnNext.enable();
	} else {
		btnNext.disable();
	}

	if (curSketch>0) {
		btnPrevious.enable();
	} else {
		btnPrevious.disable();
	}

}

function loadSketch(_curSketch) {
	curSketch = _curSketch;

	if (curSketch<0) curSketch=0;
	if (curSketch>sketches.length-1) curSketch=sketches.length-1;

	var id = sketches[curSketch];

	console.log('sketch: loadSketch curSketch',curSketch,'id',id);

	$.get(wifiboxURL + "/sketch", {id:id}, function(response) {
		if (response.status=='success') {
			console.log('sketch: loaded',response);
			var svgData = response.data.data;
			loadFromSvg(svgData);
			setSketchModified(false);
			sketchLoaded = true;
		} else {
			console.log('error loading sketch: ',response);
			listSketches();
		}
		
	})
}

function saveSketch() {
	//console.log("sketch: saveSketch");
	var svgData = saveToSvg();

	//alert(wifiboxCGIBinURL + "/sketch/new(halihallo)" + "#########" + svgData);
	
	//var response = location.href(wifiboxCGIBinURL + "/sketch/new(halihallo)");
	//alert(response);
	data = svgData.replace(/\"/g,'\'');
	
	alert(data);

	$.post(wifiboxCGIBinURL + "/sketch/new(" + data + ")", function(response) {
		//console.log("sketch: saveSketch: response",response);
		//listSketches();
		alert(response);
	})
	
	//$.post(wifiboxURL + "sketches/test.php", {data: svgData}, function(response) {
		//console.log("sketch: saveSketch: response",response);
		//listSketches();
		//alert(response);
	//})
	
	//data = svgData;
	
	//$.post( wifiboxURL + "/sketches/test.html", function( data ) {
  		//$( ".result" ).html( data );
	//});
	
	//$.post( wifiboxURL + "sketches/test.php", {data: svgData}, function( response ) {
  		//alert( "Data Loaded: " + response );
	//});
	
	//$.post(wifiboxURL + "sketches/test.php", {data: svgData});
	//$.post(wifiboxURL + "sketches/test.php");
	
	alert("Fertig!");

}

/*
 * This file is part of the Doodle3D project (http://doodle3d.com).
 *
 * Copyright (c) 2013, Doodle3D
 * This software is licensed under the terms of the GNU GPL v2 or later.
 * See file LICENSE.txt or visit http://www.gnu.org/licenses/gpl.html for full license details.
 */

// http://stackoverflow.com/questions/1403888/get-url-parameter-with-jquery
function getURLParameter(name) {
  return decodeURI(
    (new RegExp('[&?]'+name + '=' + '(.+?)(&|$)').exec(location.search)||[,null])[1]
  );
}

// returns true for all smartphones and tablets
function isMobileDevice() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Windows Mobile/i.test(navigator.userAgent);
}

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
/*
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

var printer =  new Printer();
var progressbar = new Progressbar();
var thermometer = new Thermometer();
var settingsWindow = new SettingsWindow();
var message = new Message();

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
  
  if (getURLParameter("d") != "null") debugMode = (getURLParameter("d") == "1");
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

  initDoodleDrawing();
  initPreviewRendering();
  initLayouting();
  // initSidebars();
  initButtonBehavior();
  initKeyboard();
  // initVerticalShapes();
  initWordArt();
  initShapeDialog();
  initScanDialog();

  disableDragging();
  
  if (!clientInfo.isSmartphone) initHelp();

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
});

function disableDragging() {
  $(document).bind("dragstart", function(event) {
    console.log("dragstart");
    event.preventDefault();
  });
}

function showOrHideThermo() {
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
  
}
