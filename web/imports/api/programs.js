import { Meteor } from 'meteor/meteor';
import { Mongo } from 'meteor/mongo';
import { check } from 'meteor/check';

import { Observations } from './observations.js';
import { Sessions } from './sessions.js';

export const Programs = new Mongo.Collection('programs');

// publish the programs
if (Meteor.isServer) {
    // create the publication
    Meteor.publish('programs', function() {
	return Programs.find({ owner: this.userId });
    });
}

Meteor.methods({
    'programs.insert'(name, executor) {

	// validate parameters
	check(name, String);
	check(executor, String);

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	    return;
	}

	// get all programs of the current user
	const userPrograms = Programs.find({ owner: Meteor.userId() }).fetch();
	const programNames = userPrograms.map(function(item)
					      { return item.name; });

	// check that user doesn't have program with same name
	if (programNames.indexOf(name) != -1) {
	    return;
	}
	
	// insert programs
	Programs.insert({
	    name: name,
	    executor: executor, 
	    owner: Meteor.userId(),
	    email: Meteor.user().emails[0]["address"],
	    completed: false,
	    sessions: [],
	    observations: [],
	    createdAt: new Date(), 
	});
    },

    'programs.remove'(progId) {
	check(progId, String);

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	}

	// check that the user owns the observation
	prog = Programs.find(progId).fetch();

	// found the program
	if (prog) {
	    	// cannot delete 'General' program
	    if (prog.name == "General") {
		return;
	    }

	    // check that user is the owner
	    if (Meteor.userId() === prog[0].owner) {

		// delete all sessions
		Sessions.remove({ programId: progId});

		// delete all observations
		Observations.remove({ programId: progId});

		// delete program
		Programs.remove(progId);
	    }
	}
    },

    'programs.setCompleted'(progId, completed) {
	check(progId, String);

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	}

	// mark the program as completed
	Programs.update(progId, {$set: {completed: completed}});
    }, 

});

