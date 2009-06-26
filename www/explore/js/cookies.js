function setCookie(name, val) {
  if (!name) {return false;}
  // nullify any existing cookie crumb with this name
  var cookieList = document.cookie.split(';');
  for (var x = 0; x < cookieList.length; x++) {
    var cookie = cookieList[x]
    while(cookie.charAt(0) == ' '){cookie = cookie.substr(1, cookie.length)}
    cookie = cookie.split('=');
    if( cookie[0] == escape(name) || cookie[0] == name) {
    	cookieList[x] = null;
    }
  }
  // add specified crumb to cookie
  document.cookie = new Array(escape(name) + "=" + escape(val), 'path=/ead/').concat(cookieList).join(';');
}

function getCookie(name) {
  var cookieList = document.cookie.split(';');
  for (var x = 0; x < cookieList.length; x++) {
    var cookie = cookieList[x]
    while(cookie.charAt(0) == ' '){cookie = cookie.substr(1, cookie.length)}
    cookie = cookie.split('=');
    if( cookie[0] == escape(name) || cookie[0] == name) { 
      return unescape(cookie[1]); 
    }
  }
  return '';
}
