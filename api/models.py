from neomodel import StructuredNode, StringProperty, IntegerProperty, RelationshipTo, RelationshipFrom


class User(StructuredNode):
    user_id = IntegerProperty(unique_index=True, required=True)
    name = StringProperty()
    sex = IntegerProperty()
    home_town = StringProperty()
    city = StringProperty()
    followers_count = IntegerProperty(default=0)
    follows = RelationshipFrom('User', 'Follow')
    subscriptions = RelationshipTo('Group', 'Subscribe')


class Group(StructuredNode):
    group_id = IntegerProperty(unique_index=True, required=True)
    name = StringProperty()
    subscribers_count = IntegerProperty(default=0)
    subscribed_by = RelationshipFrom('User', 'Subscribe')
