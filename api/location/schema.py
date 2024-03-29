import graphene
from sqlalchemy import func
from graphql import GraphQLError
from graphene_sqlalchemy import SQLAlchemyObjectType

from api.location.models import Location as LocationModel
from api.devices.models import Devices as DevicesModel  # noqa: F401
from api.room.models import Room as RoomModel
from api.room_resource.models import Resource as ResourceModel  # noqa: F401
from api.room.schema import Room
from utilities.validations import (
    validate_empty_fields,
    validate_url,
    validate_country_field,
    validate_timezone_field)
from utilities.utility import update_entity_fields
from helpers.email.email import notification
from helpers.auth.error_handler import SaveContextManager
from helpers.auth.user_details import get_user_from_db
from helpers.room_filter.room_filter import room_join_location
from helpers.auth.authentication import Auth
from helpers.auth.admin_roles import admin_roles


class Location(SQLAlchemyObjectType):
    """
        Autogenerated return type of a Location
    """
    class Meta:
        model = LocationModel


class CreateLocation(graphene.Mutation):
    """
        Returns location payload on creating a location
    """
    class Arguments:
        name = graphene.String(required=True)
        abbreviation = graphene.String(required=True)
        country = graphene.String(required=True)
        image_url = graphene.String()
        time_zone = graphene.String(required=True)
        state = graphene.String()
        structure = graphene.String()
    location = graphene.Field(Location)

    @Auth.user_roles('Admin')
    def mutate(self, info, **kwargs):
        # Validate if the country given is a valid country
        validate_country_field(**kwargs)
        validate_timezone_field(**kwargs)
        validate_url(**kwargs)
        validate_empty_fields(**kwargs)
        location = LocationModel(**kwargs)
        admin = get_user_from_db()
        email = admin.email
        username = email.split("@")[0]
        admin_name = username.split(".")[0]
        subject = 'A new location has been added'
        template = 'location_success.html'
        payload = {
            'model': LocationModel, 'field': 'name', 'value':  kwargs['name']
            }
        with SaveContextManager(location, 'Location', payload):
            if not notification.send_email_notification(
                email=email, subject=subject, template=template,
                location_name=location.name, user_name=admin_name
            ):
                raise GraphQLError(
                    "Location created but email not sent"
                    )
            return CreateLocation(location=location)


class UpdateLocation(graphene.Mutation):
    """
        Returns location payload on updating a location
    """
    class Arguments:
        location_id = graphene.Int()
        name = graphene.String()
        abbreviation = graphene.String()
        country = graphene.String()
        image_url = graphene.String()
        time_zone = graphene.String()
        structure = graphene.String()
    location = graphene.Field(Location)

    @Auth.user_roles('Admin')
    def mutate(self, info, location_id, **kwargs):
        location = Location.get_query(info)
        result = location.filter(LocationModel.state == "active")
        location_object = result.filter(
            LocationModel.id == location_id).first()
        if not location_object:
            raise GraphQLError("Location not found")
        admin_roles.verify_admin_location(location_id)
        if "time_zone" in kwargs:
            validate_timezone_field(**kwargs)
        if "country" in kwargs:
            validate_country_field(**kwargs)
        if "image_url" in kwargs:
            validate_url(**kwargs)
        validate_empty_fields(**kwargs)
        active_locations = result.filter(
            LocationModel.name == kwargs.get('name'))
        if active_locations:
            pass
        else:
            raise AttributeError("Not a valid location")
        update_entity_fields(location_object, **kwargs)
        location_object.save()
        return UpdateLocation(location=location_object)


class DeleteLocation(graphene.Mutation):
    """
        Returns location payload on deleting a location
    """
    class Arguments:
        location_id = graphene.Int(required=True)
        state = graphene.String()

    location = graphene.Field(Location)

    @Auth.user_roles('Admin')
    def mutate(self, info, location_id, **kwargs):
        query = Location.get_query(info)
        result = query.filter(LocationModel.state == "active")
        location = result.filter(
            LocationModel.id == location_id).first()  # noqa: E501
        if not location:
            raise GraphQLError("location not found")
        admin_roles.verify_admin_location(location_id)
        update_entity_fields(location, state="archived", **kwargs)
        location.save()
        return DeleteLocation(location=location)


class Query(graphene.ObjectType):
    """
        Query for locations
    """
    all_locations = graphene.List(
        Location,
        description="Returns a list of all locations")
    get_rooms_in_a_location = graphene.List(
        lambda: Room,
        location_id=graphene.Int(),
        description="Returns all rooms in a location. Accepts the argument\
            \n- location_id: Unique key indentifier of a location"
    )

    def resolve_all_locations(self, info):
        query = Location.get_query(info)
        result = query.filter(LocationModel.state == "active")
        return result.order_by(func.lower(LocationModel.name)).all()

    def resolve_get_rooms_in_a_location(self, info, location_id):
        query = Room.get_query(info)
        active_rooms = query.filter(RoomModel.state == "active")
        exact_query = room_join_location(active_rooms)
        result = exact_query.filter(LocationModel.id == location_id)
        return result.all()


class Mutation(graphene.ObjectType):
    create_location = CreateLocation.Field(
        description="Creates a new location given the arguments\
            \n- name: The name field of the location[required]\
            \n- abbreviation: The abbreviation field of the a location[required\
            \n- country: The country field of the location[required]\
            \n- image_url: The image url field of a location\
            \n- time_zone: The timezone of a specific location[required]\
            \n- state: Check if the location is created")
    update_location = UpdateLocation.Field(
        description="Updates a location given the arguments\
            \n- location_id: The unique identifier of the location\
            \n- name: The name field of the location[required]\
            \n- abbreviation: The abbreviation field of the a location[required\
            \n- country: The country field of the location[required]\
            \n- image_url: The image url field of a location[required]\
            \n- time_zone: The timezone of a specific location[required]")
    delete_location = DeleteLocation.Field(
        description="Deletes a given location taking the arguments\
            \n- location_id: The unique identifier of the location[required]\
            \n- state: Check if the location is active, archived or deleted")
