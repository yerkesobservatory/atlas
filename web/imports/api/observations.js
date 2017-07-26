import { Meteor } from 'meteor/meteor';
import { Mongo } from 'meteor/mongo';
import { check } from 'meteor/check';

import { Programs } from './programs.js';

export const Observations = new Mongo.Collection('observations');

// publish the observations
if (Meteor.isServer) {
    // create the publication
    Meteor.publish('observations', function() {
	if (Roles.userIsInRole(this.userId, 'admin')) {
	    return Observations.find();
	} else {
	    return Observations.find({ owner: this.userId });
	}
    });
}


Meteor.methods({
    'observations.insert'(progId, target, exptime, expcount, binning, filters) {

	// validate parameters
	check(progId, String);
	check(target, String);
	check(Number(exptime), Number);
	check(Number(expcount), Number);
	check(Number(binning), Number);
	check(filters, Array);

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	}
	
	// insert the observation
	const obsId = Observations.insert({
	    programId: progId, 
	    target: target,
	    exposure_time: Number(exptime),
	    exposure_count: Number(expcount),
	    binning: Number(binning),
	    filters: filters,
	    owner: Meteor.userId(),
	    email: Meteor.user().emails[0]["address"],
	    completed: false,
	    execDate: null,
	});

	// add the observation to the program
	Programs.update(progId, {$addToSet: { observations: obsId}});
    },

    'observations.remove'(obsId) {
	check(obsId, String);

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	}
	
	// remove observation from program
	const programId = Observations.findOne(obsId).programId;
	Programs.update(programId, {$pull: {observations: obsId}});
	    
	// remove observation
	Observations.remove({ _id: obsId, owner: Meteor.userId()});

    },
    
    'observations.setCompleted'(obsId, completed) {
	check(obsId, String);

	// check that the user is logged in
	if (! Meteor.userId()) {
	    throw new Meteor.Error('not-authorized');
	}

	// check that the user owns the observation
	Observations.update(obsId, {$set: {completed: completed}});
    }, 

});
