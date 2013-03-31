$(function() {
  // start the icon carousel
  $('#iconCarousel').carousel({
    interval: 5000
  });

  // make code pretty
  window.prettyPrint && prettyPrint();

  // inject twitter & github counts
  $.ajax({
    url: 'https://api.github.com/repos/foosel/OctoPrint',
    dataType: 'jsonp',
    success: function(data) {
      $('#watchers').html(data.data.watchers);
      $('#forks').html(data.data.forks);
    }
  });

  // inject flattr counts
  $.ajax({
    url: 'https://api.flattr.com/rest/v2/things/1179085',
    dataType: 'json',
    success: function(data) {
      $('#flattrs').html(data.flattrs);
    }
  });

  (function() {
      var s = document.createElement('script'), t = document.getElementsByTagName('script')[0];
      s.type = 'text/javascript';
      s.async = true;
      s.src = 'http://api.flattr.com/js/0.6/load.js?mode=auto';
      t.parentNode.insertBefore(s, t);
  })();

  // G+
  (function() {
      var po = document.createElement('script'); po.type = 'text/javascript'; po.async = true;
      po.src = 'https://apis.google.com/js/plusone.js';
      var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(po, s);
  })();
});
