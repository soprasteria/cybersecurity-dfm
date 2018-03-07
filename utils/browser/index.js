var loadJson = function() {

  $.getJSON('data/connector.json', function(json) {
    var pulmo = new Pulmo.default('#docs');
    pulmo.loadJson(json);
  });

}

$(document).ready(function() {
  loadJson();

  var panelTop = null;
  $(window).scroll(function(){

    if(!panelTop) {
      panelTop = $('.panel').position().top;
    }

    var fromTop = $(window).scrollTop();
    var marginTop = panelTop - fromTop;

    if(marginTop < 100) {
      marginTop = 100;
    };

    $(".panel").css('top', marginTop);

  });
});
