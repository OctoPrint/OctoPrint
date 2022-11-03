# General TODOs

  * Protocols
    * Firmware detection vs connection sequence, warnings trigger too late/not at all
  * Transports
    * "no serial ports" warning
  * Anything missing from settings migration to profile?
  * Disconnect after incomplete connect/reset states
  * Failing tests

---

On disconnect from (virtual) printer:

```
2021-12-16 17:45:05,197 - tornado.application - ERROR - Uncaught exception POST /api/connection (127.0.0.1)
HTTPServerRequest(protocol='http', host='localhost:5000', method='POST', uri='/api/connection', version='HTTP/1.1', remote_ip='127.0.0.1')
Traceback (most recent call last):
  File "d:\Code\OctoPrint\devenv37\lib\site-packages\tornado\web.py", line 1702, in _execute
    result = method(*self.path_args, **self.path_kwargs)
  File "d:\code\octoprint\octoprint\src\octoprint\server\util\tornado.py", line 591, in _handle_method
    self._fallback(self.request, body)
  File "d:\code\octoprint\octoprint\src\octoprint\server\util\tornado.py", line 702, in __call__
    WsgiInputContainer.environ(request, body), start_response
  File "d:\Code\OctoPrint\devenv37\lib\site-packages\flask\app.py", line 2076, in wsgi_app
    response = self.handle_exception(e)
  File "d:\Code\OctoPrint\devenv37\lib\site-packages\flask\app.py", line 2073, in wsgi_app
    response = self.full_dispatch_request()
  File "d:\Code\OctoPrint\devenv37\lib\site-packages\flask\app.py", line 1518, in full_dispatch_request
    rv = self.handle_user_exception(e)
  File "d:\Code\OctoPrint\devenv37\lib\site-packages\flask\app.py", line 1516, in full_dispatch_request
    rv = self.dispatch_request()
  File "d:\Code\OctoPrint\devenv37\lib\site-packages\flask\app.py", line 1502, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**req.view_args)
  File "d:\code\octoprint\octoprint\src\octoprint\server\util\flask.py", line 1560, in decorated_view
    return func(*args, **kwargs)
  File "d:\code\octoprint\octoprint\src\octoprint\vendor\flask_principal.py", line 196, in _decorated
    rv = f(*args, **kw)
  File "d:\code\octoprint\octoprint\src\octoprint\server\api\connection.py", line 102, in connectionCommand
    printer.disconnect()
  File "d:\code\octoprint\octoprint\src\octoprint\printer\standard.py", line 614, in disconnect
    self._protocol.unregister_listener(self)
AttributeError: 'NoneType' object has no attribute 'unregister_listener'
2021-12-16 17:45:05,198 - octoprint.events.fire - DEBUG - Firing event: Disconnecting (Payload: None)
```

---

TBC
