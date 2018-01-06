import './profile.html';
import { Meteor } from 'meteor/meteor';
import $ from 'jquery';
import { Observations } from '../api/observations.js';
import { Accounts } from 'meteor/accounts-base';

Template.profile.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('observations');
});

Template.profile.helpers({
    user() {
	return Meteor.user();
    },
    numPending(user) {
	if (user) {
	    return Observations.find({'owner': user._id,
				      'completed': false}).count();
	}
    },
    numCompleted(user) {
	if (user) {
	    return Observations.find({'owner': user._id,
				      'completed': true}).count();
	}
    },

    badges(user) {
	if (user) {
	    return ['Explorer', ' Kronian', ' Harperian'];
	}
    },
});

// Template.editProfile.helpers({
//     user() {
// 	return Meteor.user();
//     },
// });

Template.profile.events({
    'click #editProfile': function(e) {
	e.preventDefault();

	// show the modal for the current user
	id = Meteor.userId();
	Modal.show('editProfile', function () {
	    // Under no circumstances, replace `id` below
	    // with Meteor.userId(). MAJOR BUG.
	    // See comment by Soitech:
	    // https://github.com/PeppeL-G/bootstrap-3-modal/issues/5
	    if (Meteor.users.findOne(id)) {
		return Meteor.users.findOne(id);
	    }
	});
    }
});

// called when "change password" button is pressed
Template.editProfile.events({
    'submit .changePassword'(event) {
	// prevent default submission
	event.preventDefault();

	// clear notifications
	CoffeeAlerts.clearSeen();

	// clear 'success' formatting from form
	$('.change-password').find('.form-group').removeClass('has-success');

	// extract values
	const target = event.target;
	const currentPassword = target.currentPassword.value;
	const password = target.password.value;
	const passwordRepeat = target.passwordRepeat.value;

	// if passwords do not match
	if (password != passwordRepeat) {
	    return;
	}

	// id of user to change
	const id = Template.instance().data._id;

	// TODO: Check security of password

	// check that current password matches
	const digest = Accounts._hashPassword(currentPassword);
	result = Meteor.call('users.checkPassword', id, digest,  function(err, result) {
	    if (result) {
		// change their password for them
		Meteor.call('users.setPassword', id, passwordRepeat, function(error) {
		    if (error) {
			CoffeeAlerts.error(error.message);
		    } else {
			CoffeeAlerts.success('Password successfully changed.');
		    }
		});
	    } else {
		CoffeeAlerts.error('The current password is incorrect.');
	    }
	});

	// clear form values
	$('input[type="password"]').val('');

	// TODO: Move CoffeeAlert into modal


    }
});
