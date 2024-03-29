from datetime import datetime
import graphene
from helpers.auth.authentication import Auth
from graphene_sqlalchemy import SQLAlchemyObjectType
from api.response.models import Response as ResponseModel
from utilities.validations import validate_empty_fields
from graphql import GraphQLError
from api.room.schema import Room
from api.question.models import Question as QuestionModel
from helpers.pagination.paginate import ListPaginate
from helpers.response.create_response import create_response


class Response(SQLAlchemyObjectType):
    """
        Autogenerated return type of a response
    """
    class Meta:
        model = ResponseModel


class ResponseDetail(graphene.ObjectType):
    response_id = graphene.Int()
    suggestion = graphene.String()
    missing_items = graphene.List(graphene.String)
    created_date = graphene.DateTime()
    rating = graphene.Int()
    resolved = graphene.Boolean()


class RoomResponses(graphene.ObjectType):
    room_id = graphene.Int()
    room_name = graphene.String()
    total_responses = graphene.Int()
    response = graphene.List(ResponseDetail)


class PaginatedResponse(graphene.ObjectType):
    pages = graphene.Int()
    query_total = graphene.Int()
    has_next = graphene.Boolean()
    has_previous = graphene.Boolean()
    current_page = graphene.Int()
    responses = graphene.List(RoomResponses)


class ResponseInputs(graphene.InputObjectType):
    question_id = graphene.Int(
        required=True, description="Unique identifier field of a question")
    rate = graphene.Int(description="Id field of where the response is made")
    text_area = graphene.String(description="The rate field of response inputs")
    missing_items = graphene.List(
        graphene.Int, description="Number field of the missing items")


class CreateResponse(graphene.Mutation):
    """
        Returns response payload on creating a response
    """
    class Arguments:
        responses = graphene.List(ResponseInputs, required=True)
        room_id = graphene.Int(required=True)

    response = graphene.List(Response)

    def mutate(self, info, **kwargs):
        validate_empty_fields(**kwargs)
        query = Room.get_query(info)
        responses = []
        errors = []
        present_date = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        room = query.filter_by(id=kwargs['room_id']).first()
        if not room:
            raise GraphQLError("Non-existent room id")
        for each_response in kwargs['responses']:
            question = QuestionModel.query.filter_by(
                id=each_response.question_id).first()
            if not question:
                errors.append(
                    "Response to question {} was not saved because it does not exist".format(each_response.question_id)) # noqa
                continue
            if present_date < question.start_date:
                errors.append(
                    "The start date for the response to this question is yet to commence. Try on {}".format(question.start_date)) # noqa
            question_type = question.question_type
            each_response['room_id'] = kwargs['room_id']
            responses, errors = create_response(question_type,
                                                errors,
                                                responses,
                                                **each_response)
        if errors:
            raise GraphQLError(
                ('The following errors occured: {}').format(
                    str(errors).strip('[]'))
                )
        return CreateResponse(response=responses)


class Query(graphene.ObjectType):
    """
        Query to get the room response
    """
    get_room_response = graphene.Field(
        PaginatedResponse,
        room_id=graphene.Int(),
        page=graphene.Int(),
        per_page=graphene.Int(),
        description="Returns a list of responses of a room. Accepts the arguments\
            \n- room_id: Unique identifier of a room\
            \n- page: Page number of responses\
            \n- per_page: Number of room responses per page")

    def map_room_responses(self, responses):
        mapped_response = []
        missing_resource = []
        for response in responses:
            response_id = response.id
            suggestion = response.text_area
            created_date = response.created_date
            rating = response.rate
            resolved = response.resolved
            if len(response.missing_resources) > 0:
                for resource in response.missing_resources:
                    resource_name = resource.name
                    missing_resource.append(resource_name)
                response_in_room = ResponseDetail(
                    response_id=response_id,
                    suggestion=suggestion,
                    created_date=created_date,
                    rating=rating,
                    missing_items=missing_resource,
                    resolved=resolved)
                mapped_response.append(response_in_room)
            else:
                missing_items = response.missing_resources
                response_in_room = ResponseDetail(
                    response_id=response_id,
                    suggestion=suggestion,
                    created_date=created_date,
                    rating=rating,
                    missing_items=missing_items,
                    resolved=resolved)
                mapped_response.append(response_in_room)
        return mapped_response

    @Auth.user_roles('Admin')
    def resolve_get_room_response(self, info, **kwargs):
        # Get the room's feedback
        page = kwargs.get('page')
        per_page = kwargs.get('per_page')
        query = Response.get_query(info)
        room_feedback = query.filter_by(room_id=kwargs['room_id'])
        if room_feedback.count() < 1:
            raise GraphQLError("This room\
 doesn't exist or doesn't have feedback.")

        if page and per_page:
            responses = room_feedback.offset((page * per_page) - per_page)\
                .limit(per_page)
            paginated_response = ListPaginate(
                iterable=room_feedback.all(),
                per_page=per_page,
                page=page)
            has_previous = paginated_response.has_previous
            has_next = paginated_response.has_next
            current_page = paginated_response.page
            pages = paginated_response.pages
            query_total = paginated_response.query_total

            mapped_responses = Query.map_room_responses(self, responses)
            all_room_responses = []
            room_response = RoomResponses(response=mapped_responses,
                                          room_id=kwargs['room_id'],
                                          total_responses=len(mapped_responses),
                                          room_name=room_feedback[0].room.name)
            all_room_responses.append(room_response)
            return PaginatedResponse(responses=all_room_responses,
                                     has_previous=has_previous,
                                     has_next=has_next,
                                     query_total=query_total,
                                     current_page=current_page,
                                     pages=pages)

        mapped_responses = Query.map_room_responses(self, room_feedback)
        all_room_responses = []
        room_response = RoomResponses(response=mapped_responses,
                                      room_id=kwargs['room_id'],
                                      total_responses=len(mapped_responses),
                                      room_name=room_feedback[0].room.name)
        all_room_responses.append(room_response)
        return PaginatedResponse(responses=all_room_responses)


class HandleRoomResponse(graphene.Mutation):
    """
        Returns payload on marking or unmarking
        a response as resolved
    """
    class Arguments:
        response_id = graphene.Int()

    room_response = graphene.Field(Response)

    @Auth.user_roles('Admin')
    def mutate(self, info, response_id, **kwargs):
        query_responses = Response.get_query(info)
        room_response = query_responses.filter(
            ResponseModel.id == response_id).first()
        if not room_response:
            raise GraphQLError("Response does not exist")
        if room_response.resolved:
            room_response.resolved = False
            room_response.save()
        else:
            room_response.resolved = True
            room_response.save()
        return HandleRoomResponse(room_response=room_response)


class Mutation(graphene.ObjectType):
    create_response = CreateResponse.Field(
        description="Mutation to create a new response taking the arguments\
            \n- responses: Field for the response inputs\
            \n- room_id: Unique key identifier of the room where the response \
            is made")
    resolve_room_response = HandleRoomResponse.Field(
        description="Mutation to mark or unmark a response as resolved\
            \n- room_response: Field for the response inputs\
            \n- response_id: Unique key identifier of a room_response"
    )
