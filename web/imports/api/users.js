import { Meteor } from 'meteor/meteor';
import { Mongo } from 'meteor/mongo';
import { check } from 'meteor/check';

import { Programs } from './programs.js';
import { Observations } from './observations.js';
import { Sessions } from './sessions.js';

// publish user affiliations
export const Affiliations = new Mongo.Collection('affiliations');

// publish affiliations and useres
if (Meteor.isServer) {

    // users
    Meteor.publish('users', function() {
	if (Roles.userIsInRole(this.userId, 'admin')) {
	    return Meteor.users.find({}, {fields: {profile: 1, emails: 1}});
	} else {
	    // user not authorized
	    this.stop();
	    return;
	}});

    // publications
    Meteor.publish('affiliations', function() {
	return Affiliations.find({});
    });
}

Meteor.methods({
    'users.insert'(email, profile) {
	if (Meteor.isServer) { 
	    const id = Accounts.createUser({
		email: email,
		profile: profile})

	    // add to user
	    Roles.addUsersToRoles(id, ['users']);

	    if (id) {	    
		// send enrollment email
		Accounts.sendEnrollmentEmail(id);
	    } else {
		CoffeeAlerts.error('Unable to create user...');
	    }
	}
    }, 

    'users.remove'(userId) {
	check(userId, String);

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	}

	if (Roles.userIsInRole(Meteor.userId(), 'admin')) {

	    // delete all programs (this should also delete obs and sessions)
	    Programs.remove({owner: userId});

	    // just to be safe, delete all obs and sessions
	    Observations.remove({owner: userId});
	    Sessions.remove({owner: userId});

	    // delete user
	    Meteor.users.remove(userId);
	}
    },

    'users.toggleAdmin'(userId) {

	// verify
	check(userId, String);

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	}

	// toggle the users admin state
	if (Roles.userIsInRole(userId, 'admins')) {
	    Roles.removeUsersFromRoles(userId, 'admins');
	    Roles.addUsersToRoles(userId, 'users');
	} else if (Roles.userIsInRole(userId, 'users')) {
	    Roles.addUsersToRoles(userId, 'admins');
	    Roles.removeUsersFromRoles(userId, 'users');
	}
    },
    
    'affiliations.insert'(name) {

	// validate parameters
	check(name, String);

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	    return;
	}

	// insert affiliations
	Affiliations.insert({
	    name: name,
	});
    },

    'affiliations.remove'(affilId) {
	check(affilId, String);

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	}

	Affiliations.remove(affilId);
    }, 

});

