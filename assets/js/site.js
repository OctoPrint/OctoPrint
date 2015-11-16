$(function() {
  // start the screenshot carousel
  $('#screenshot-carousel').carousel({
    interval: 5000
  });

  // make code pretty
  window.prettyPrint && prettyPrint();

  // G+
  (function() {
      var po = document.createElement('script'); po.type = 'text/javascript'; po.async = true;
      po.src = 'https://apis.google.com/js/plusone.js';
      var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(po, s);
  })();
});
