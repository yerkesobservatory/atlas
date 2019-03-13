import { Meteor } from 'meteor/meteor';
import { Mongo } from 'meteor/mongo';
import { check } from 'meteor/check';

import { Programs } from './programs.js';

export const Observations = new Mongo.Collection('observations');

function availableTime() {
    var observations = Observations.find({owner: Meteor.userId(), completed: false }).fetch();

    // total time of observations that the user has in the queue
    totalTime =  _.reduce(observations, function(sum, next) {
        return sum + next.totalTime;
    }, 0);

    // get the number of credits that the user has
    user = Meteor.user();
    if (user) {
        allowedTime = Meteor.user().maxQueueTime;
        // return how many seconds the user is allowed left
        return allowedTime - totalTime;
    } else {
        return "Unknown";
    }
}


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
    ReactiveTable.publish("my_observations", Observations,
                          function () {
                              return {"owner": this.userId};
                          },
                          {"disablePageCountReactivity": true});

    ReactiveTable.publish("completed_observations", Observations,
                          function () {
                              return {"owner": this.userId, "completed": true};
                          },
                          {"disablePageCountReactivity": true});

    ReactiveTable.publish("pending_observations", Observations,
                          function () {
                              return {"owner": this.userId, "completed": false};
                          },
                          {"disablePageCountReactivity": true});

}

Meteor.methods({
    'observations.insert'(progId, target, exptime, expcount, binning, filters, options) {
        //, priority) {

        // validate parameters
        check(progId, String);
        check(target, String);
        check(Number(exptime), Number);
        check(Number(expcount), Number);
        check(Number(binning), Number);
        check(filters, Array);
        check(options, Object);

        // check that the user is logged in
        if (! Meteor.userId()) {
            throw new Meteor.Error('not-authorized');
        }

        // check that the user has enough available credits
        if (Number(exptime)*Number(expcount)*filters.length > availableTime()) {
            throw new Meteor.Error('not-enough-credits');
        }

        // insert the observation
        const obsId = Observations.insert({
            program: progId,
            target: target,
            exposure_time: Number(exptime),
            exposure_count: Number(expcount),
            binning: Number(binning),
            filters: filters,
            options: options,
            owner: Meteor.userId(),
            email: Meteor.user().emails[0]["address"],
            completed: false,
            execDate: null,
            createdAt: new Date(),
            totalTime: Number(exptime)*Number(expcount)*filters.length
            // priority: Meteor.user().priority
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
        const program = Observations.findOne(obsId).program;
        Programs.update(program, {$pull: {observations: obsId}});

        // remove observation
        Observations.remove({_id: obsId, owner: Meteor.userId()});

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

    'observations.totalAvailableTime'() {
        return availableTime();
    }
});
