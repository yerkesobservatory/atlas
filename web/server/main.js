import { Meteor } from 'meteor/meteor';
import { Random } from 'meteor/random';

// import routing
import '../imports/router.js'

// import API code
import '../imports/api/observations.js';
import '../imports/api/sessions.js';
import '../imports/api/programs.js';
import '../imports/api/users.js';

Meteor.startup(() => {
    // code to run on server at startup

    // there are no usrs
    if (! Meteor.users.findOne()) {

	// create a user
	const password = Random.id();
	const id = Accounts.createUser({
	    email: 'newaccount@admin.com',
	    password: password
	});

	// make the user an admin
	Roles.addUsersToRoles(id, 'admin');

	// print the password
	console.log("Created new account with password: "+password);
    }
});

(function () {
    "use strict";

    Accounts.urls.resetPassword = function (token) {
	return Meteor.absoluteUrl('reset/' + token);
    };

    Accounts.urls.enrollAccount = function (token) {
    	return Meteor.absoluteUrl('reset/' + token);
    };

    Accounts.emailTemplates.from = 'Stone Edge Observatory <sirius.stonedgeobservatory@gmail.com>';
    Accounts.emailTemplates.siteName = 'Stone Edge Observatory';

    // setup enrollment email
    Accounts.emailTemplates.enrollAccount.text = (user, url) => {
	return 'Welcome to Atlas @ Stone Edge Observatory!\n\n'
	    + 'To activate your account, please click the link below:\n\n'
	    + url;
    };
    Accounts.emailTemplates.enrollAccount.subject = (user, url) => {
	return 'Your new Stone Edge Observatory account';
    };

    // configure password reset message
    Accounts.emailTemplates.resetPassword.text = (user, url) => {
	return 'Hello from Atlas @ Stone Edge Observatory!\n\n'
	    + 'Your password has been successfully reset; to set your'
	    + ' new password, please click the link below. \n\n'
	    + url;
    };
    Accounts.emailTemplates.resetPassword.subject = (user, url) => {
	return 'Resetting your password for Atlas @ Stone Edge Observatory';
    };

})();

