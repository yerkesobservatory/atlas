import { Meteor } from 'meteor/meteor';
import { Mongo } from 'meteor/mongo';
import { check } from 'meteor/check';

import { Programs } from './programs.js';

export const Sessions = new Mongo.Collection('sessions');

// publish the sessions
if (Meteor.isServer) {
    // create the publication
    Meteor.publish('sessions', function() {
	return Sessions.find();
    });
}

Meteor.methods({
    'sessions.insert'(programId, startDate, endDate) {
	// validate parameters
	check(programId, String); // id of program
	check(startDate, String); // start datetime
	check(endDate, String); // end datetime

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	}

	// parse dates
	const start = new Date(startDate);
	const end = new Date(endDate);

	// insert session into database
	sessionId = Sessions.insert({
	    programId: programId, 
	    start: start, 
	    end: end, 
	    owner: Meteor.userId(),
	    email: Meteor.user().emails[0]["address"],
	    completed: false
	});

	// if successful, add session to program
	Programs.update(programId, {$addToSet: {sessions: sessionId}});

    },

    'sessions.remove'(sessionId) {
	// checks
	check(sessionId, String);
	
	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	}

	const ownerId = Sessions.findOne(sessionId).owner;

	if (ownerId == Meteor.userId()) {
	
	    // find programId of session
	    const progId = Sessions.findOne(sessionId).programId;

	    // remove session from program
	    prog = Programs.update(progId, {$pull: {sessions: sessionId}});

	    // remove session
	    Sessions.remove(sessionId);
	}

    },

});
