import './login.html';

import $ from 'jquery';

Template.login.events({
    'submit .login'(event) {

	// prevent default submission
	event.preventDefault();

	// extract values
	const target = event.target;
	const email = target.email.value;
	const password  = target.password.value;

	// attempt login
	Meteor.loginWithPassword(email, password, function(error) {
	    if (error) {
		if (error.reason == 'error.accounts.Login forbidden') {
      $('.modal-backdrop').remove();
      //TODO Alerts should appear in modal
      //$('#messageModal').modal('show');
		    // clear the existing login messages
		    CoffeeAlerts.clearSeen()
		    CoffeeAlerts.error('Incorrect username or password');

		} else {
		    CoffeeAlerts.error(error.message);
		}
	    }
      else {
        //fade out modal
        $('.modal-backdrop').remove();
      }
	});

    }
});
