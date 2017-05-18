'use strict';

/**
	* Save options globally. It will be available in every browser of the same user.
*/

function saveOptions() {
	var dfmAddress = document.getElementById('dfmAddress').value;
	var firstName = document.getElementById('firstName').value;
	var lastName = document.getElementById('lastName').value;

	chrome.storage.sync.set({
		dfmAddress: dfmAddress,
		firstName: firstName,
		lastName: lastName
	}, function () {
		// Just print a message to inform the user that his datas have been saved.

		var status = document.getElementById('status');
		status.textContent = 'Options saved.';
		setTimeout(function () {
			status.textContent = '';
		}, 750)
	})
}

/**
	* Pre fill the options.
*/
function restoreOptions() {
  chrome.storage.sync.get({
    dfmAddress: 'http://localhost:12345/api/chromeplugin',
    firstName: 'dfm',
    lastName: 'user'
  }, function(items) {
    document.getElementById('dfmAddress').value = items.dfmAddress;
    document.getElementById('firstName').value = items.firstName;
    document.getElementById('lastName').value = items.lastName;
  });
}

/**
	* Add a listener to get when is the option loaded.
	* Add a listener to the save button.
*/

document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('saveOptions').addEventListener('click', saveOptions);