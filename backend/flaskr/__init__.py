import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10


# utility for paginating questions
def paginate_questions(request, selection):
    page = request.args.get('page', 1, type=int)
    start = (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE

    questions = [question.format() for question in selection]
    current_questions = questions[start:end]

    return current_questions


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)

    # set up CORS, allowing all origins
    CORS(app, resources={'/': {'origins': '*'}})

    @app.after_request
    def after_request(response):
        '''
        Sets access control.
        '''
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type,Authorization,true')
        response.headers.add('Access-Control-Allow-Methods',
                             'GET,PUT,POST,DELETE,OPTIONS')
        return response

    @app.route('/categories')
    def get_categories():
        '''
        Handles GET requests for getting all categories.
        '''

        # get all categories and add to dict
        categories = Category.query.all()
        categories_dict = {}
        for category in categories:
            categories_dict[category.id] = category.type

        # abort 404 if no categories found
        if (len(categories_dict) == 0):
            abort(404)

        # return data to view
        return jsonify({
            'success': True,
            'categories': categories_dict
        })

    @app.route('/questions')
    def get_questions():
        '''
        Handles GET requests for getting all questions.
        '''

        # get all questions and paginate
        selection = Question.query.all()
        total_questions = len(selection)
        current_questions = paginate_questions(request, selection)

        # get all categories and add to dict
        categories = Category.query.all()
        categories_dict = {}
        for category in categories:
            categories_dict[category.id] = category.type

        # abort 404 if no questions
        if (len(current_questions) == 0):
            abort(404)

        # return data to view
        return jsonify({
            'success': True,
            'questions': current_questions,
            'total_questions': total_questions,
            'categories': categories_dict
        })

    @app.route('/questions/<int:id>', methods=['DELETE'])
    def delete_question(id):
        '''
        Handles DELETE requests for deleting a question by id.
        '''

        try:
            # get the question by id
            question = Question.query.filter_by(id=id).one_or_none()

            # abort 404 if no question found
            if question is None:
                abort(404)

            # delete the question
            question.delete()

            # return success response
            return jsonify({
                'success': True,
                'deleted': id
            })

        except:
            # abort if problem deleting question
            abort(422)

    @app.route('/questions', methods=['POST'])
    def post_question():
        '''
        Handles POST requests for creating new questions and searching questions.
        '''
        # load the request body
        body = request.get_json()

        # if search term is present
        if (body.get('searchTerm')):
            search_term = body.get('searchTerm')

            # query the database using search term
            selection = Question.query.filter(
                Question.question.ilike(f'%{search_term}%')).all()

            # 404 if no results found
            if (len(selection) == 0):
                abort(404)

            # paginate the results
            paginated = paginate_questions(request, selection)

            # return results
            return jsonify({
                'success': True,
                'questions': paginated,
                'total_questions': len(Question.query.all())
            })
        # if no search term, create new question
        else:
            # load data from body
            new_question = body.get('question')
            new_answer = body.get('answer')
            new_difficulty = body.get('difficulty')
            new_category = body.get('category')

            # ensure all fields have data
            if ((new_question is None) or (new_answer is None)
                    or (new_difficulty is None) or (new_category is None)):
                abort(422)

            try:
                # create and insert new question
                question = Question(question=new_question, answer=new_answer,
                                    difficulty=new_difficulty, category=new_category)
                question.insert()

                # get all questions and paginate
                selection = Question.query.order_by(Question.id).all()
                current_questions = paginate_questions(request, selection)

                # return data to view
                return jsonify({
                    'success': True,
                    'created': question.id,
                    'question_created': question.question,
                    'questions': current_questions,
                    'total_questions': len(Question.query.all())
                })

            except:
                # abort unprocessable if exception
                abort(422)

    @app.route('/categories/<int:id>/questions')
    def get_questions_by_category(id):
        '''
        Handles GET requests for getting questions based on category.
        '''

        # get the category by id
        category = Category.query.filter_by(id=id).one_or_none()

        # abort 400 for bad request if category isn't found
        if (category is None):
            abort(400)

        # get the matching questions
        selection = Question.query.filter_by(category=category.id).all()

        # paginate the selection
        paginated = paginate_questions(request, selection)

        # return the results
        return jsonify({
            'success': True,
            'questions': paginated,
            'total_questions': len(Question.query.all()),
            'current_category': category.type
        })

    @app.route('/quizzes', methods=['POST'])
    def get_random_quiz_question():
        '''
        Handles POST requests for playing quiz.
        '''

        # load the request body
        body = request.get_json()

        # get the previous questions
        previous = body.get('previous_questions')

        # get the category
        category = body.get('quiz_category')

        # abort 400 if category or previous questions isn't found
        if ((category is None) or (previous is None)):
            abort(400)

        # load questions all questions if "ALL" is selected
        if (category['id'] == 0):
            questions = Question.query.all()
        # load questions for given category
        else:
            questions = Question.query.filter_by(category=category['id']).all()

        # get total number of questions
        total = len(questions)

        # picks a random question
        def get_random_question():
            return questions[random.randrange(0, len(questions), 1)]

        # checks to see if question has already been used
        def check_if_used(question):
            used = False
            for q in previous:
                if (q == question.id):
                    used = True

            return used

        # get random question
        question = get_random_question()

        # check if used, execute until unused question found
        while (check_if_used(question)):
            question = get_random_question()

            # if all questions have been tried, return without question
            # necessary if category has <5 questions
            if (len(previous) == total):
                return jsonify({
                    'success': True
                })

        # return the question
        return jsonify({
            'success': True,
            'question': question.format()
        })

# error handlers

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": 404,
            "message": "resource not found"
        }), 404

    @app.errorhandler(422)
    def unprocessable(error):
        return jsonify({
            "success": False,
            "error": 422,
            "message": "unprocessable"
        }), 422

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "success": False,
            "error": 400,
            "message": "bad request"
        }), 400

    return app
