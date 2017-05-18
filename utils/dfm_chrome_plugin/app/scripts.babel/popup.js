'use strict';

chrome.tabs.query({'active': true, 'lastFocusedWindow': true}, function (tabs) {
	document.getElementById('urlToSend').value = tabs[0].url;
});

/**
	* Send the url from the chrome plugin to the dfm address stored in the options.
*/

function sendUrl() {

	// Getting options from chrome storage. They are stored globally.

	chrome.storage.sync.get({
		dfmAddress: 'http://localhost:12345/api/chromeplugin',
		firstName: 'dfm',
		lastName: 'user'
	}, function(items) {
		var urlToSend = document.getElementById('urlToSend').value;
		var firstname = items.firstName;
		var lastname = items.lastName;
		var dfmUrl = items.dfmAddress;
		var data = {};

		data = {
			firstname: firstname,
			lastname: lastname,
			link: urlToSend,
			dfm: dfmUrl,
			keywords: []
		};
		var http = new XMLHttpRequest();

		http.open('POST', dfmUrl, true);
		http.setRequestHeader('Content-type', 'application/json');
		http.onreadystatechange = function() {
			if (http.readyState == 4 && http.status == 200) {
				console.log(http.responseText);
			}
		}
		http.send(JSON.stringify(data));
	})
}

/**
	* Set the name of the user in the chrome plugin.
*/

function setName() {
	chrome.storage.sync.get({
		dfmAddress: 'http://localhost:12345/api/chromeplugin',
		firstName: 'dfm',
		lastName: 'user'
	}, function(items) {
		document.getElementById('name').textContent = items.firstName + ' ' + items.lastName;
	});
}

/**
	* Add a listener to get when is the option loaded.
	* Add a listener to the save button.
*/

document.addEventListener('DOMContentLoaded', setName);
document.getElementById('sendUrl').addEventListener('click', sendUrl);