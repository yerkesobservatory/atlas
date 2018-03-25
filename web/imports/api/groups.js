import { Meteor } from 'meteor/meteor';
import { Mongo } from 'meteor/mongo';
import { check } from 'meteor/check';

// publish user groups
export const Groups = new Mongo.Collection('groups');

// publish groups and users
if (Meteor.isServer) {

    // publications
    Meteor.publish('groups', function() {
        return Groups.find({});
    });
}

// methods
Meteor.methods({
    'groups.insert'(name, priority, defaultPriority, defaultMaxQueueTime) {

        // validate parameters
        check(name, String);
        check(priority, Number);
        check(defaultPriority, Number);
        check(defaultMaxQueueTime, Number);

        // checkp that the user is logged in
        if (! Meteor.userId()) {
            throw new Meteor.Error('not-authorized');
            return;
        }

        // check that the values are sensible
        if ((priority < 1) || (defaultMaxQueueTime < 0) || (defaultPriority < 0)) {
            throw new Meteor.Error('invalid-parameters');
            return;
        }

        // insert groups
        Groups.insert({
            name: name,
            priority: priority,
            defaultPriority: defaultPriority,
            defaultMaxQueueTime: defaultMaxQueueTime
        });
    },

    'groups.remove'(groupId) {
        check(groupId, String);

        // check that the user is logged in
        if (! Meteor.userId()) {
            throw new Meteor.Error('not-authorized');
        }

        Groups.remove(groupId);
    }
});
