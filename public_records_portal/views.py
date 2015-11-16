"""
    public_records_portal.views
    ~~~~~~~~~~~~~~~~

    Implements functions that render the Jinja (http://jinja.pocoo.org/) templates/html for RecordTrac.

"""

from flask import flash
from flask import render_template, redirect, url_for, send_from_directory
from flask.ext.login import login_user, logout_user, current_user, login_required
# from flaskext.browserid import BrowserID
from public_records_portal import db, models, recaptcha
from prr import add_resource, update_resource, make_request, close_request, add_note, add_public_note
from db_helpers import authenticate_login, get_user_by_id
import os
import json
from urlparse import urlparse, urljoin
from notifications import format_date
from spam import is_spam, is_working_akismet_key, check_for_spam
from time import time
from flask import jsonify, request, Response
import anyjson
import csv_export
from datetime import datetime, timedelta
import dateutil.parser
from filters import *
import re
from db_helpers import get_count, get_obj
from sqlalchemy import func, and_, or_, text
from forms import OfflineRequestForm, NewRequestForm, LoginForm, EditUserForm
import pytz
from requires_roles import requires_roles
from flask_login import LoginManager
from models import AnonUser
from datetime import datetime, timedelta, date
from business_calendar import Calendar
cal = Calendar()

# Initialize login
app.logger.info("\n\nInitialize login.")
app.logger.info("\n\nEnvironment is %s" % app.config['ENVIRONMENT'])

login_manager = LoginManager()
login_manager.user_loader(get_user_by_id)
login_manager.anonymous_user = AnonUser
login_manager.init_app(app)

zip_reg_ex = re.compile('^[0-9]{5}(?:-[0-9]{4})?$')
@app.before_request
def make_session_permanent():
    app.permanent_session_lifetime = timedelta(minutes=120)


# Submitting a new request
@app.route("/new", methods=["GET", "POST"])
def new_request(passed_recaptcha=False, data=None):
    form = None
    departments = None
    routing_available = False
    errors = []
    if request.method == 'POST':
        if current_user.is_authenticated:
            form = OfflineRequestForm(request.form)
            request_agency = current_user.current_department.name
            request_summary = form.request_summary.data
            request_text = form.request_text.data
            request_attachment_description = form.request_attachment_description.data
            request_attachment = form.request_attachment.data
            request_format = form.request_format.data
            request_date = form.request_date.data
            request_first_name = form.request_first_name.data
            request_last_name = form.request_last_name.data
            request_role = form.request_role.data
            request_organization = form.request_organization.data
            request_email = form.request_email.data
            request_phone = form.request_phone.raw_data
            request_phone = re.sub("\D", "",str(request_phone))
            request_fax = form.request_fax.raw_data
            request_fax = re.sub("\D", "",str(request_fax))
            request_address_street_one = form.request_address_street_one.data
            request_address_street_two = form.request_address_street_two.data
            request_address_city = form.request_address_city.data
            request_address_state = form.request_address_state.data
            request_address_zip = form.request_address_zip.data

            # Check Summary
            if not (request_summary and request_summary.strip()):
                errors.append('You must enter a summary for this request')
            elif len(request_summary) > 250:
                errors.append(
                    'The request summary must be less than 250 characters')
            # Check Description of Request
            if not (request_text and request_text.strip()):
                errors.append('You must enter a description for this request')
            elif len(request_summary) > 5000:
                errors.append(
                    'The request description must be less than 5000 characters')
            try:
                request_attachment = request.files['request_attachment']
            except:
                app.logger.info("\n\nNo file passed in")

            # Check Attachment
            if request_attachment_description and not (request_attachment):
                errors.append('Please select a file to upload as attachment.')

            if not (request_text and request_text.strip()):
                errors.append('Please fill out the request description.')

            # Check Format
            if not (request_format and request_format.strip()):
                errors.append(
                    'You must enter the format in which the request was received')

            # Check Date
            if request_date:
                try:
                    tz = pytz.timezone(str(app.config['TIMEZONE']))
                    offset = tz.utcoffset(datetime.now())
                    offset = (offset.days * 86400 + offset.seconds) / 3600
                    # request_date = request_date - timedelta(hours=offset)
                except TypeError:
                    errors.append(
                        "Please use the datepicker to select a date.")
                    request_date = None
                except ValueError:
                    errors.append(
                        "Please use the datepicker to select a date.")
                    request_date = None
            else:
                errors.append("Please use the datepicker to select a date.")

            if not (request_first_name and request_first_name.strip()):
                errors.append("Please enter the requester's first name")
            elif not (request_last_name and request_last_name.strip()):
                errors.append("Please enter the requester's last name")
            else:
                alias = request_first_name + " " + request_last_name

            zip_reg_ex = re.compile('^[0-9]{5}(?:-[0-9]{4})?$')
            email_valid = (request_email != '')
            phone_valid = (request_phone is not None)
            fax_valid = (request_fax is not None)
            street_valid = (request_address_street_one != '')
            city_valid = (request_address_city != '')
            state_valid = (request_address_state != '')
            zip_valid = (
                request_address_zip != '' and zip_reg_ex.match(request_address_zip))
            address_valid = (
                street_valid and city_valid and state_valid and zip_valid)

            if not (email_valid or phone_valid or fax_valid or address_valid):
                errors.append(
                    "Please enter at least one type of contact information")

            if not data:
                data = request.form.copy()

            if errors:
                if request_date:
                    return render_template('offline_request.html', form=form, date=request_date.strftime('%m/%d/%Y'),
                                           routing_available=routing_available,
                                           departments=departments, errors=errors)
                return render_template('offline_request.html', form=form,
                                       routing_available=routing_available, departments=departments, errors=errors)
            else:
                request_id, is_new = make_request(
                    agency=request_agency,
                    summary=request_summary,
                    text=request_text,
                    attachment=request_attachment,
                    attachment_description=request_attachment_description,
                    offline_submission_type=request_format,
                    date_received=request_date,
                    first_name=request_first_name,
                    last_name=request_last_name,
                    alias=str(request_first_name + ' ' + request_last_name),
                    role=request_role,
                    organization=request_organization,
                    email=request_email,
                    phone=request_phone,
                    fax=request_fax,
                    street_address_one=request_address_street_one,
                    street_address_two=request_address_street_two,
                    city=request_address_city,
                    state=request_address_state,
                    zip=request_address_zip)
                if is_new == False:
                    errors.append(
                        "Looks like your request is the same as /request/%s" % request_id)
                    return render_template('offline_request.html', form=form,
                                           routing_available=routing_available, departments=departments, errors=errors)

                return redirect(url_for('show_request_for_x', request_id=request_id,
                                        audience='new', email=(request_email is not None)))

        else:
            form = NewRequestForm(request.form)
            print form.data
            print request.form
            request_agency = form.request_agency.data
            request_summary = form.request_summary.data
            request_text = form.request_text.data
            request_first_name = form.request_first_name.data
            request_last_name = form.request_last_name.data
            request_role = form.request_role.data
            request_organization = form.request_organization.data
            request_email = form.request_email.data
            request_phone = form.request_phone.raw_data
            request_phone = re.sub("\D", "",str(request_phone))
            request_fax = form.request_fax.raw_data
            request_fax = re.sub("\D", "",str(request_fax))
            request_address_street_one = form.request_address_street_one.data
            request_address_street_two = form.request_address_street_two.data
            request_address_city = form.request_address_city.data
            request_address_state = form.request_address_state.data
            request_address_zip = form.request_address_zip.data

            request_id, is_new = make_request(
                agency=request_agency,
                summary=request_summary,
                text=request_text,
                first_name=request_first_name,
                last_name=request_last_name,
                alias=str(request_first_name + ' ' + request_last_name),
                role=request_role,
                organization=request_organization,
                email=request_email,
                phone=request_phone,
                fax=request_fax,
                street_address_one=request_address_street_one,
                street_address_two=request_address_street_two,
                city=request_address_city,
                state=request_address_state,
                zip=request_address_zip)

            if is_new == False:
                errors.append(
                    "Looks like your request is the same as <a href=\"/request/%s\"" % request_id)
                return render_template('new_request.html', form=form,
                                   routing_available=routing_available, departments=departments, errors=errors)
            return redirect(url_for('show_request_for_x', request_id=request_id,
                                    audience='new', email=(request_email is not None)))

    elif request.method == 'GET':
        if 'LIAISONS_URL' in app.config:
            routing_available = True
        if current_user.is_authenticated and current_user.role in ['Portal Administrator', 'Agency Administrator',
                                                                     'Agency FOIL Personnel']:
            form = OfflineRequestForm()
            return render_template('offline_request.html', form=form, routing_available=routing_available)
        else:
            form = NewRequestForm()
            return render_template('new_request.html', form=form, routing_available=routing_available)

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/export")
@login_required
def to_csv():
    filename = request.form.get('filename', 'records.txt')
    return Response(csv_export.export(),
        mimetype='text/plain',
        headers = {
            'Content-Disposition': 'attachment; filename="%s"' % (filename,)
        })

@app.route("/", methods=["GET", "POST"])
def index():
    if current_user.is_anonymous == False:
        return redirect(url_for('display_all_requests'))
    else:
        return landing()


@app.route("/landing")
def landing():
    return render_template('landing.html')


@login_manager.unauthorized_handler
def unauthorized():
    app.logger.info("\n\nuser is unauthorized.")
    return render_template("alpha.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


def explain_all_actions():
    action_json = open(os.path.join(app.root_path, 'static/json/actions.json'))
    json_data = json.load(action_json)
    actions = []
    for data in json_data:
        actions.append("%s: %s" % (data, json_data[data]["What"]))
    return render_template('actions.html', actions=actions)

# Returns a view of the case based on the audience. Currently views exist for city staff or general public.


@app.route("/<string:audience>/request/<string:request_id>")
def show_request_for_x(audience, request_id):
    if "city" in audience:
        return show_request_for_city(request_id=request_id)
    return show_request(request_id=request_id, template="manage_request_%s.html" % (audience))


show_request_for_x.methods = ['GET', 'POST']


@app.route("/city/request/<string:request_id>")
@login_required
@requires_roles('Portal Administrator', 'Agency Administrator', 'Agency FOIL Personnel', 'Agency Helpers')
def show_request_for_city(request_id):
    req = get_obj("Request", request_id)
    if current_user.role == 'Agency Helpers':
        audience = 'helper'
    else:
        audience = 'city'
    return show_request(request_id=request_id, template="manage_request_%s_less_js.html" % (audience))

@app.route("/response/<string:request_id>")
def show_response(request_id):
    req = get_obj("Request", request_id)
    if not req:
        return render_template('error.html', message="A request with ID %s does not exist." % request_id)
    return render_template("response.html", req=req)


@app.route("/track", methods=["GET","POST"])
def track(request_id=None):
    if request.method == 'POST':
        if not request_id:
            request_id = request.form['request_id']
        if not current_user.is_anonymous:
            audience = 'city'
        else:
            audience = 'public'

        return redirect(url_for('fetch_requests', request_id_search=request_id))
    else:
        return render_template("track.html")


@app.route("/unfollow/<string:request_id>/<string:email>")
def unfollow(request_id, email):
    success = False
    user_id = create_or_return_user(email.lower())
    subscriber = get_subscriber(request_id=request_id, user_id=user_id)
    if subscriber:
        success = update_obj(attribute="should_notify", val=False, obj=subscriber)
    if success:
        return show_request(request_id=request_id, template="manage_request_unfollow.html")
    else:
        return render_template('error.html',
                               message="Unfollowing this request was unsuccessful. You probably weren't following it to begin with.")


@app.route("/request/<string:request_id>")
def show_request(request_id, template="manage_request_public.html"):
    req = get_obj("Request", request_id)
    departments_all = models.Department.query.all()
    agency_data = []
    for d in departments_all:
        primary_contact = d.primary_contact
        agency_data.append({'name': d.name, 'email': primary_contact.email})

    if not req:
        return render_template('error.html', message="A request with ID %s does not exist." % request_id)
    else:
        users = models.User.query.filter_by(department_id=req.department_id).all()

    if req.status and "Closed" in req.status and template != "manage_request_feedback.html":
        template = "closed.html"

    department = models.Department.query.filter_by(id=req.department_id).first()
    assigned_user = models.User.query.filter_by(
        id=models.Owner.query.filter_by(request_id=request_id, is_point_person=True).first().user_id).first()
    helpers = []
    for i in req.owners:
        if not i.active or i.is_point_person:
            continue
        helper = models.User.query.filter_by(id=i.user_id).first()
        if helper:
            helpers.append({'name': helper.alias, 'email': helper.email})

    print helpers

    return render_template(template, req=req, agency_data=agency_data, users=users,
                           department=department, assigned_user=assigned_user, helpers=helpers)


@app.route("/api/staff")
def staff_to_json():
    users = models.User.query.filter(models.User.is_staff == True).all()
    staff_data = []
    for u in users:
        staff_data.append({'alias': u.alias, 'email': u.email})
    return jsonify(**{'objects': staff_data})


@app.route("/api/departments")
def departments_to_json():
    departments = models.Department.query.all()
    agency_data = []
    for d in departments:
        agency_data.append({'agency': d.name})
    return jsonify(**{'objects': agency_data})


def docs():
    return redirect('http://codeforamerica.github.io/public-records/docs/1.0.0')


@app.route("/edit/request/<string:request_id>")
@login_required
def edit_case(request_id):
    req = get_obj("Request", request_id)
    return render_template("edit_case.html", req=req)


@app.route("/add_a_<string:resource>", methods=["GET", "POST"])
@login_required
def add_a_resource(resource):
    req = request.form
    if request.method == 'POST':
        print "Resource is a ", resource
        if resource == 'pdf':
            return add_resource(resource=resource, request_body=request.form, current_user_id=get_user_id())
        resource_id = add_resource(resource=resource, request_body=request.form, current_user_id=get_user_id())
        if type(resource_id) == int or str(resource_id).isdigit():
            app.logger.info("\n\nSuccessfully added resource: %s with id: %s" % (resource, resource_id))
            return redirect(url_for('show_request_for_city', request_id=request.form['request_id']))
        elif resource_id == False:
            app.logger.info("\n\nThere was an issue with adding resource: %s" % resource)
            return render_template('error.html')
        else:
            app.logger.info("\n\nThere was an issue with the upload: %s" % resource_id)
            return render_template('help_with_uploads.html', message=resource_id)
    return render_template('error.html', message="You can only update requests from a request page!")

@app.route("/public_add_a_<string:resource>", methods = ["GET", "POST"])
def public_add_a_resource(resource, passed_recaptcha = False, data = None):
    if (data or request.method == 'POST') and ('note' in resource or 'subscriber' in resource):
            if not data:
                    data = request.form.copy()
            if 'note' in resource:
                if not passed_recaptcha and is_spam(comment = data['note_text'], user_ip = request.remote_addr, user_agent = request.headers.get('User-Agent')):
                    return render_template('recaptcha_note.html', form = data, message = "Hmm, your note looks like spam. To submit your note, type the numbers or letters you see in the field below.")
                resource_id = prr.add_note(request_id = data['request_id'], text = data['note_text'])
            else:
                resource_id = prr.add_resource(resource = resource, request_body = data, current_user_id = None)
            if type(resource_id) == int:
                request_id = data['request_id']
                audience = 'public'
                if 'subscriber' in resource:
                    audience = 'follower'
                return redirect(url_for('show_request_for_x', audience=audience, request_id = request_id))
    return render_template('error.html')


@app.route("/update_a_<string:resource>", methods=["GET", "POST"])
def update_a_resource(resource, passed_recaptcha=False, data=None):
    if (data or request.method == 'POST'):
        req=request.form
        if not data:
            data = request.form.copy()
        if 'owner' in resource:
            update_resource(resource, req)

        elif 'qa' in resource:
            prr.answer_a_question(qa_id=int(data['qa_id']), answer=data['answer_text'], passed_spam_filter=True)
        else:
            update_resource(resource, data)
        if current_user.is_authenticated:
            return redirect(url_for('show_request_for_city', request_id=request.form['request_id']))
        else:
            return redirect(url_for('show_request', request_id=request.form['request_id']))
    return render_template('error.html', message="You can only update requests from a request page!")


@app.route("/acknowledge_request", methods=["GET", "POST"])
def acknowledge_request(resource, passed_recaptcha=False, data=None):
    if (data or request.method == 'POST'):
        if not data:
            data = request.form.copy()
        if 'qa' in resource:
            prr.answer_a_question(qa_id=int(data['qa_id']), answer=data['acknowledge_request'], passed_spam_filter=True)
        else:
            update_resource(resource, data)
        if current_user.is_anonymous == False:
            return redirect(url_for('show_request_for_city', request_id=request.form['request_id']))
        else:
            return redirect(url_for('show_request', request_id=request.form['request_id']))
    return render_template('error.html', message="You can only update requests from a request page!")

# Closing is specific to a case, so this only gets called from a case (that only city staff have a view of)

@app.route("/close", methods=["GET", "POST"])
@login_required
def close(request_id=None):
    if request.method == 'POST':
        template = 'closed.html'
        request_id = request.form['request_id']
        reason = ""
        if 'close_reason' in request.form:
            reason = request.form['close_reason']
        elif 'close_reasons' in request.form:
            for close_reason in request.form.getlist('close_reasons'):
                reason += close_reason + " "
        close_request(request_id=request_id, reason=reason, user_id=get_user_id(), request_body=request.form)
        return show_request(request_id, template=template)
    return render_template('error.html', message="You can only close from a requests page!")

def filter_agency(departments_selected, results):
    if departments_selected and 'All departments' not in departments_selected:
        app.logger.info("\n\nagency filters:%s." % departments_selected)
        department_ids = []
        for department_name in departments_selected:
            if department_name:
                department = models.Department.query.filter_by(name=department_name).first()
                if department:
                    department_ids.append(department.id)
        if department_ids:
            results = results.filter(models.Request.department_id.in_(department_ids))
        else:
            # Just return an empty query set
            results = results.filter(models.Request.department_id < 0)
    return results

def filter_search_term(search_input, results):
    if search_input:
        app.logger.info("Searching for '%s'." % search_input)
        search_terms = search_input.strip().split(
            " ")  # Get rid of leading and trailing spaces and generate a list of the search terms
        num_terms = len(search_terms)
        # Set up the query
        search_query = ""
        if num_terms > 1:
            for x in range(num_terms - 1):
                search_query = search_query + search_terms[x] + ' & '
        search_query = search_query + search_terms[num_terms - 1] + ":*"  # Catch substrings
        results = results.filter("to_tsvector(text) @@ to_tsquery('%s')" % search_query)
    return results

def filter_request_id(request_id_search, results):
    if request_id_search:
        app.logger.info("Searching for matching request_id '%s'." % filter_request_id)
        request_id_search = request_id_search.strip() # Get rid of leading and trailing spaces
        request_id_search = request_id_search + ":*"  # Catch substrings
        results = results.filter(text("to_tsvector(id) @@ to_tsquery('%s')" % request_id_search))
    return results

def get_filter_value(filters_map, filter_name, is_list=False, is_boolean=False):
    if filter_name in filters_map:
        val = filters_map[filter_name]
        if filter_name == 'agency' and val:
            return [val]
        elif is_list:
            return filters_map.getlist(filter_name)
        elif is_boolean:
            return str(val.lower())
        else:
            return val
    return None


def is_supported_browser():
    browser = request.user_agent.browser
    version = request.user_agent.version and int(request.user_agent.version.split('.')[0])
    platform = request.user_agent.platform
    uas = request.user_agent.string
    if browser and version:
        if (browser == 'msie' and version < 9) \
                or (browser == 'firefox' and version < 4) \
                or (platform == 'android' and browser == 'safari' and version < 534) \
                or (platform == 'iphone' and browser == 'safari' and version < 7000) \
                or ((platform == 'macos' or platform == 'windows') and browser == 'safari' and not re.search('Mobile',
                                                                                                             uas) and version < 534) \
                or (re.search('iPad', uas) and browser == 'safari' and version < 7000) \
                or (platform == 'windows' and re.search('Windows Phone OS', uas)) \
                or (browser == 'opera') \
                or (re.search('BlackBerry', uas)):
            return False
        return False
    return False


@app.route("/view_requests", methods=["GET"])
def display_all_requests():
    return no_backbone_requests()


@app.route("/view_requests_backbone")
def backbone_requests():
    return render_template("all_requests.html", departments=db.session.query(models.Department).all(),
                           total_requests_count=get_count("Request"))


@app.route("/view_requests_no_backbone")
def no_backbone_requests():
    return fetch_requests()


@app.route("/requests", methods=["GET"])
def fetch_requests(output_results_only=False, filters_map=None, date_format='%Y-%m-%d', checkbox_value='on'):

    user_id = get_user_id()

    # Sets the search parameters. They are a dictionary that either came in through:
    # 1) json_requests() (endpoint used by backbone)
    # 2) request.args (arguments in the URL)
    # 3) the form submitted
    if not filters_map:
        if request.args:
            if is_supported_browser():
                return backbone_requests()
            else:  # Clear URL
                filters_map = request.args
        else:
            filters_map = request.form

    # Set defaults
    is_open = checkbox_value
    is_closed = None
    # in_progress = checkbox_value
    due_soon = checkbox_value
    overdue = checkbox_value
    mine_as_poc = checkbox_value
    mine_as_helper = checkbox_value
    departments_selected = []
    if current_user.is_authenticated:
        departments_selected.append(current_user.current_department.name)
    sort_column = "id"
    sort_direction = "asc"
    min_due_date = None
    max_due_date = None
    min_date_received = None
    max_date_received = None
    requester_name = None
    page_number = 1
    search_term = None
    request_id_search = None

    if filters_map:
        departments_selected = get_filter_value(filters_map=filters_map, filter_name='departments_selected',
                                                is_list=True) or get_filter_value(filters_map, 'department')
        is_open = get_filter_value(filters_map=filters_map, filter_name='is_open', is_boolean=True)
        # in_progress = get_filter_value(filters_map=filters_map, filter_name='in_progress', is_boolean=True)
        is_closed = get_filter_value(filters_map=filters_map, filter_name='is_closed', is_boolean=True)
        due_soon = get_filter_value(filters_map=filters_map, filter_name='due_soon', is_boolean=True)
        overdue = get_filter_value(filters_map=filters_map, filter_name='overdue', is_boolean=True)
        mine_as_poc = get_filter_value(filters_map=filters_map, filter_name='mine_as_poc', is_boolean=True)
        mine_as_helper = get_filter_value(filters_map=filters_map, filter_name='mine_as_helper', is_boolean=True)
        sort_column = get_filter_value(filters_map, 'sort_column') or 'id'
        sort_direction = get_filter_value(filters_map, 'sort_direction') or 'asc'
        search_term = get_filter_value(filters_map, 'search_term')
        min_due_date = get_filter_value(filters_map, 'min_due_date')
        max_due_date = get_filter_value(filters_map, 'max_due_date')
        min_date_received = get_filter_value(filters_map, 'min_date_received')
        max_date_received = get_filter_value(filters_map, 'max_date_received')
        requester_name = get_filter_value(filters_map, 'requester_name')
        page_number = int(get_filter_value(filters_map, 'page_number') or '1')
        request_id_search = get_filter_value(filters_map, 'request_id_search')

    # Set initial checkboxes for mine_as_poc and mine_as_helper when redirected from login page
    if request.referrer and 'login' in request.referrer:
        if current_user.is_authenticated and (current_user.role in ['Portal Administrator', 'Agency Administrator'] or current_user.is_admin()):
            mine_as_poc = None
            mine_as_helper = None
        elif current_user.is_authenticated and current_user.role in ['Agency FOIL Personnel']:
            mine_as_poc = "on"
            mine_as_helper = "on"
        elif current_user.is_authenticated and current_user.role in ['Agency Helpers']:
            mine_as_poc = "on"

    results = get_results_by_filters(departments_selected=departments_selected, is_open=is_open, is_closed=is_closed,
                                     due_soon=due_soon, overdue=overdue, mine_as_poc=mine_as_poc,
                                     mine_as_helper=mine_as_helper, sort_column=sort_column,
                                     sort_direction=sort_direction, search_term=search_term, min_due_date=min_due_date,
                                     max_due_date=max_due_date, min_date_received=min_date_received,
                                     max_date_received=max_date_received, requester_name=requester_name,
                                     page_number=page_number, user_id=user_id, date_format=date_format,
                                     checkbox_value=checkbox_value, request_id_search=request_id_search)

    # Execute query
    limit = 15
    offset = limit * (page_number - 1)
    app.logger.info("Page Number: {0}, Limit: {1}, Offset: {2}".format(page_number, limit, offset))
    more_results = False
    num_results = results.count()
    start_index = 0
    end_index = 0

    if num_results != 0:
        start_index = (page_number - 1) * limit
        if start_index == 0:
            start_index = 1
        if num_results > (limit * page_number):
            more_results = True
            end_index = start_index + 14
        else:
            end_index = num_results

    results = results.limit(limit).offset(offset).all()
    requests = prepare_request_fields(results=results)
    if output_results_only == True: # Used by json_requests()
        return requests, num_results, more_results, start_index, end_index

    return render_template("all_requests_less_js.html", total_requests_count=get_count("Request"), requests=requests,
                           departments=db.session.query(models.Department).all(),
                           departments_selected=departments_selected, is_open=is_open, is_closed=is_closed,
                           due_soon=due_soon, overdue=overdue, mine_as_poc=mine_as_poc, mine_as_helper=mine_as_helper,
                           sort_column=sort_column, sort_direction=sort_direction, search_term=search_term,
                           min_due_date=min_due_date, max_due_date=max_due_date, min_date_received=min_date_received,
                           max_date_received=max_date_received, requester_name=requester_name, page_number=page_number,
                           more_results=more_results, num_results=num_results, start_index=start_index,
                           end_index=end_index)


@app.route("/custom/request", methods=["GET", "POST"])
def json_requests():
    """
    Ultra-custom API endpoint for serving up requests.
    Supports limit, search, and page parameters and returns json with an object that
    has a list of results in the 'objects' field.
    """
    objects, num_results, more_results, start_index, end_index = fetch_requests(output_results_only=True,
                                                                                filters_map=request.args,
                                                                                date_format='%m/%d/%Y',
                                                                                checkbox_value='true')
    matches = {
        "objects": objects,
        "num_results": num_results,
        "more_results": more_results,
        "start_index": start_index,
        "end_index": end_index
    }
    response = anyjson.serialize(matches)
    return Response(response, mimetype="application/json")


def prepare_request_fields(results):
    return map(lambda r: {
        "id": r.id, \
        "summary": helpers.clean_text(r.summary), \
        "date_received": helpers.date(r.date_received or r.date_created), \
        "department": r.department_name(), \
        "requester": r.requester_name(), \
        "due_date": format_date(r.due_date), \
        "status": r.status, \
        # The following two attributes are defined as model methods,
        # and not regular SQLAlchemy attributes.
        "contact_name": r.point_person_name(), \
        "solid_status": r.solid_status()
    }, results)


def filter_department(departments_selected, results):
  if departments_selected and 'All Agencies' not in departments_selected:
      app.logger.info("\n\nagency filters:%s." % departments_selected)
      department_ids = []
      for department_name in departments_selected:
          if department_name:
              department = models.Department.query.filter_by(name=department_name).first()
              if department:
                  department_ids.append(department.id)
      if department_ids:
          results = results.filter(models.Request.department_id.in_(department_ids))
      else:
          # Just return an empty query set
          results = results.filter(models.Request.department_id < 0)
  return results


def get_results_by_filters(departments_selected, is_open, is_closed, due_soon, overdue, mine_as_poc, mine_as_helper,
                           sort_column, sort_direction, search_term, min_due_date, max_due_date, min_date_received,
                           max_date_received, requester_name, page_number, user_id, date_format, checkbox_value, request_id_search):
    # Initialize query
    results = db.session.query(models.Request)

    # Set filters on the query

    results = filter_department(departments_selected=departments_selected, results=results)
    results = filter_search_term(search_input=search_term, results=results)
    results = filter_request_id(request_id_search=request_id_search, results=results)

    # Accumulate status filters
    status_filters = []

    if is_open == checkbox_value:
        status_filters.append(models.Request.open)
        if not user_id:
            status_filters.append(models.Request.due_soon)
            status_filters.append(models.Request.overdue)

    if is_closed == checkbox_value:
        status_filters.append(models.Request.closed)

    if min_date_received and max_date_received and min_date_received != "" and max_date_received != "":
        try:
            min_date_received = datetime.strptime(min_date_received, date_format)
            max_date_received = datetime.strptime(max_date_received, date_format) + timedelta(hours=23, minutes=59)
            results = results.filter(and_(models.Request.date_received >= min_date_received,
                                          models.Request.date_received <= max_date_received))
            app.logger.info('Request Date Bounding. Min: {0}, Max: {1}'.format(min_date_received, max_date_received))
        except:
            app.logger.info('There was an error parsing the request date filters. Received Min: {0}, Max {1}'.format(
                min_date_received, max_date_received))


    # Filters for agency staff only:
    if user_id:

        if due_soon == checkbox_value:
            status_filters.append(models.Request.due_soon)

        if overdue == checkbox_value:
            status_filters.append(models.Request.overdue)

        if min_due_date and max_due_date and min_due_date != "" and max_due_date != "":
            try:
                min_due_date = datetime.strptime(min_due_date, date_format)
                max_due_date = datetime.strptime(max_due_date, date_format) + timedelta(hours=23, minutes=59)
                results = results.filter(
                    and_(models.Request.due_date >= min_due_date, models.Request.due_date <= max_due_date))
                app.logger.info('Due Date Bounding. Min: {0}, Max: {1}'.format(min_due_date, max_due_date))
            except:
                app.logger.info(
                    'There was an error parsing the due date filters. Due Date Min: {0}, Max {1}'.format(min_due_date,
                                                                                                         max_due_date))

        # PoC and Helper filters
        if mine_as_poc == checkbox_value:
            if mine_as_helper == checkbox_value:
                # Where am I the Point of Contact *or* the Helper?
                results = results.filter(models.Request.id == models.Owner.request_id) \
                    .filter(models.Owner.user_id == user_id) \
                    .filter(models.Owner.active == True)
            else:
                # Where am I the Point of Contact only?
                results = results.filter(models.Request.id == models.Owner.request_id) \
                    .filter(models.Owner.user_id == user_id) \
                    .filter(models.Owner.is_point_person == True)
        elif mine_as_helper == checkbox_value:
            # Where am I a Helper only?
            results = results.filter(models.Request.id == models.Owner.request_id) \
                .filter(models.Owner.user_id == user_id) \
                .filter(models.Owner.active == True) \
                .filter(models.Owner.is_point_person == False)
        # Filter based on requester name
        requester_name = requester_name
        if requester_name and requester_name != "":
            results = results.join(models.Subscriber, models.Request.subscribers).join(models.User).filter(
                func.lower(models.User.alias).like("%%%s%%" % requester_name.lower()))

    # Apply the set of status filters to the query.
    # Using 'or', they're non-exclusive!
    results = results.filter(or_(*status_filters))

    if sort_column:
        app.logger.info("Sort Direction: %s" % sort_direction)
        app.logger.info("Sort Column: %s" % sort_column)
        if sort_direction == "desc":
            results = results.order_by((getattr(models.Request, sort_column)).desc())
        else:
            results = results.order_by((getattr(models.Request, sort_column)).asc())

    print results
    return results.order_by(models.Request.id.desc())

@app.route("/tutorial")
def tutorial_initial():
    user_id = get_user_id()
    app.logger.info("\n\nTutorial accessed by user: %s." % user_id)
    return render_template('tutorial_01.html')

@app.route("/tutorial/<string:tutorial_id>")
def tutorial(tutorial_id):
    user_id = get_user_id()
    tutorial_string_id = tutorial_id.split("_")[0]
    app.logger.info("\n\nTutorial accessed by user: %s." % user_id)
    return render_template('tutorial_' + tutorial_string_id + '.html')

@app.route("/city/tutorial/<string:tutorial_id>")
def tutorial_agency(tutorial_id):
    if current_user.is_authenticated:
        user_id = get_user_id()
        tutorial_string_id = tutorial_id.split("_")[0]
        app.logger.info("\n\nTutorial accessed by user: %s." % user_id)
        return render_template('tutorial_agency_' + tutorial_string_id + '.html')
    else:
        return render_template("404.html"), 404
 
@app.route("/city/tutorial")
def tutorial_agency_initial():
    if current_user.is_authenticated:
        user_id = get_user_id()
        app.logger.info("\n\nTutorial accessed by user: %s." % user_id)
        return render_template('tutorial_agency_01.html')
    else:
        return render_template("404.html"), 404

@app.route("/about")
def staff_card():
    return render_template('about.html')

@app.route("/staff_card/<int:user_id>")
def about(user_id):
    return render_template('staff_card.html', uid=user_id)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def get_user_id():
    if current_user.is_authenticated:
        return current_user.id
    return None


# Used as AJAX POST endpoint to check if new request text contains certain keyword
# See new_requests.(html/js)

@app.route("/is_public_record", methods=["POST"])
def is_public_record():
    request_text = request.form['request_text']
    not_records_filepath = os.path.join(app.root_path, 'static/json/notcityrecords.json')
    not_records_json = open(not_records_filepath)
    json_data = json.load(not_records_json)
    request_text = request_text.lower()
    app.logger.info("Someone input %s" % (request_text))
    if "birth" in request_text or "death" in request_text or "marriage" in request_text:
        return json_data["Certificate"]
    if "divorce" in request_text:
        return json_data["Divorce"]
    return ''

def get_redirect_target():
    """ Taken from http://flask.pocoo.org/snippets/62/ """
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target

def is_safe_url(target):
    """ Taken from http://flask.pocoo.org/snippets/62/ """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc



@app.route("/recaptcha_<string:templatetype>", methods=["GET", "POST"])
def recaptcha_templatetype(templatetype):
    if request.method == 'POST':
        template = "recaptcha_" + templatetype + ".html"
        response = captcha.submit(
            request.form['recaptcha_challenge_field'],
            request.form['recaptcha_response_field'],
            app.config['RECAPTCHA_SECRET_KEY'],
            request.remote_addr
        )
        if not response.is_valid:
            message = "Invalid. Please try again."
            return render_template(template, message=message, form=request.form)
        else:
            if templatetype == "answer":
                app.logger.info("Template type is answer!")
                return update_a_resource(passed_recaptcha=True, data=request.form, resource="qa")
            elif templatetype == "request":
                return new_request(passed_recaptcha=True, data=request.form)
    else:
        app.logger.info("\n\nAttempted access to recaptcha not via POST")
        return render_template('error.html', message="You don't need to be here.")


@app.route("/.well-known/status", methods=["GET"])
def well_known_status():
    '''
    '''
    response = {
        'status': 'ok',
        'updated': int(time()),
        'dependencies': ['Akismet', 'Postgres'],
        'resources': {}
    }

    #
    # Try to connect to the database and get the first user.
    #
    try:
        if not get_obj('User', 1):
            raise Exception('Failed to get the first user')

    except Exception, e:
        response['status'] = 'Database fail: %s' % e
        return jsonify(response)

    #
    # Try to connect to Akismet and see if the key is valid.
    #
    # try:
    #     if not is_working_akismet_key():
    #         raise Exception('Akismet reported a non-working key')
    #
    # except Exception, e:
    #     response['status'] = 'Akismet fail: %s' % e
    #     return jsonify(response)

    return jsonify(response)


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = LoginForm()
    errors = []
    if request.method == 'POST':
        user_to_login = authenticate_login(form.username.data)
        if user_to_login:
            login_user(user_to_login)
            return render_template("edit_user.html", form=EditUserForm(), errors=[])
        errors.append("Your e-mail address must be added by an administrator before you can log in.")
    return render_template('user_registration.html', form=form, errors=errors)


@app.route("/edit_user_info", methods=['GET', 'POST'])
@login_required
def edit_user_info():
    form = EditUserForm(request.form, obj=current_user)
    errors = []
    if request.method == 'POST':
        form.populate_obj(current_user)
        db.session.add(current_user)
        db.session.commit()
        flash("User updated!")
    return render_template("edit_user.html", form=form, errors=errors)


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    errors = []
    if request.method == 'POST':
        print form.username.data
        print form.password.data
        if form.validate_on_submit():
            user_to_login = authenticate_login(form.username.data, form.password.data)
            if user_to_login:
                login_user(user_to_login)
                redirect_url = get_redirect_target()
                if 'login' in redirect_url or 'logout' in redirect_url:
                    return redirect(url_for('display_all_requests'))
                else:
                    if 'city' not in redirect_url:
                        redirect_url = redirect_url.replace("/request", "/city/request")
                    return redirect(redirect_url)
            else:
                app.logger.info(
                    "\n\nLogin failed (due to incorrect email/password combo) for email : %s" % form.username.data)
                errors.append('Incorrect email/password combination. Please try again. If you forgot your password,'
                              'please <a href="/reset_password">request a new password</a>.')
                return render_template('login.html', form=form, errors=errors)
        else:
            errors.append('Something went wrong')
            return render_template('login.html', form=form, errors=errors)
    else:
        user_id = get_user_id()
        if user_id:
            redirect_url = get_redirect_target()
            return redirect(redirect_url)
        else:
            return render_template('login.html', form=form)


@app.route("/attachments/<string:resource>", methods=["GET"])
def get_attachments(resource):
    app.logger.info("\n\ngetting attachment file")

    return send_from_directory(app.config["UPLOAD_FOLDER"], resource, as_attachment=True)

@app.route("/pdfs/<string:resource>", methods=["GET"])
def get_pdfs(resource):
    app.logger.info("\n\ngetting pdf file")
    return send_from_directory(app.config["PDF_FOLDER"], resource, as_attachment=True)


@app.route("/api/report/<string:calendar_filter>/<string:report_type>/<string:agency_filter>/<string:staff_filter>", methods=["GET"])
def get_report_jsons(calendar_filter, report_type, agency_filter, staff_filter):
    app.logger.info("\n\ngenerating report data")

    if not report_type:
        response={
            "status" : "failed: unrecognized request."
        }
        return jsonify(response)

    overdue_filter = models.Request.overdue
    notoverdue_filter = models.Request.notoverdue
    published_filter = models.Request.published
    denied_filter = models.Request.denied
    granted_and_closed_filter = models.Request.granted_and_closed
    granted_in_part_filter = models.Request.granted_in_part
    no_customer_response_filter = models.Request.no_customer_response
    out_of_jurisdiction_filter = models.Request.out_of_jurisdiction
    referred_to_nyc_gov_filter = models.Request.referred_to_nycgov
    referred_to_opendata_filter = models.Request.referred_to_opendata
    referred_to_other_agency_filter = models.Request.referred_to_other_agency
    referred_to_publications_portal_filter = models.Request.referred_to_publications_portal
    

    if report_type == "all":
        try:
            if agency_filter == "all" or agency_filter=="0":
                overdue_request=models.Request.query.filter(overdue_filter).all()
                notdue_request=models.Request.query.filter(notoverdue_filter).all()
                received_request=models.Request.query
                published_request=models.Request.query.filter(published_filter)
                denied_request=models.Request.query.filter(denied_filter).all()
                granted_and_closed_request=models.Request.query.filter(granted_and_closed_filter).all()
                granted_in_part_request=models.Request.query.filter(granted_in_part_filter).all()
                no_customer_response_request=models.Request.query.filter(no_customer_response_filter).all()
                out_of_jurisdiction_request=models.Request.query.filter(out_of_jurisdiction_filter).all()
                referred_to_nyc_gov_request=models.Request.query.filter(referred_to_nyc_gov_filter).all()
                referred_to_opendata_request=models.Request.query.filter(referred_to_opendata_filter).all()
                referred_to_other_agency_request=models.Request.query.filter(referred_to_other_agency_filter).all()
                referred_to_publications_portal_request=models.Request.query.filter(referred_to_publications_portal_filter).all()
            else:
                agencyFilterInt = int(agency_filter)
                overdue_request=models.Request.query.filter(overdue_filter).filter(models.Request.department_id == agencyFilterInt).all()
                notdue_request=models.Request.query.filter(notoverdue_filter).filter(models.Request.department_id == agencyFilterInt).all()
                received_request=models.Request.query.filter(models.Request.department_id == agencyFilterInt)
                published_request=models.Request.query.filter(published_filter).filter(models.Request.department_id == agencyFilterInt)
                denied_request=models.Request.query.filter(denied_filter).filter(models.Request.department_id == agencyFilterInt).all()
                granted_and_closed_request=models.Request.query.filter(granted_and_closed_filter).filter(models.Request.department_id == agencyFilterInt).all()
                granted_in_part_request=models.Request.query.filter(granted_in_part_filter).filter(models.Request.department_id == agencyFilterInt).all()
                no_customer_response_request=models.Request.query.filter(no_customer_response_filter).filter(models.Request.department_id == agencyFilterInt).all()
                out_of_jurisdiction_request=models.Request.query.filter(out_of_jurisdiction_filter).filter(models.Request.department_id == agencyFilterInt).all()
                referred_to_nyc_gov_request=models.Request.query.filter(referred_to_nyc_gov_filter).filter(models.Request.department_id == agencyFilterInt).all()
                referred_to_opendata_request=models.Request.query.filter(referred_to_opendata_filter).filter(models.Request.department_id == agencyFilterInt).all()
                referred_to_other_agency_request=models.Request.query.filter(referred_to_other_agency_filter).filter(models.Request.department_id == agencyFilterInt).all()
                referred_to_publications_portal_request=models.Request.query.filter(referred_to_publications_portal_filter).filter(models.Request.department_id == agencyFilterInt).all()
            if calendar_filter == "fullYear":
                overdue_request=models.Request.query.filter(overdue_filter).all()
                notdue_request=models.Request.query.filter(notoverdue_filter).all()
                received_request=models.Request.query.all()
                published_request=models.Request.query.filter(published_filter).all()
                denied_request=models.Request.query.filter(denied_filter).all()
                granted_and_closed_request=models.Request.query.filter(granted_and_closed_filter).all()
                granted_in_part_request=models.Request.query.filter(granted_in_part_filter).all()
                no_customer_response_request=models.Request.query.filter(no_customer_response_filter).all()
                out_of_jurisdiction_request=models.Request.query.filter(out_of_jurisdiction_filter).all()
                referred_to_nyc_gov_request=models.Request.query.filter(referred_to_nyc_gov_filter).all()
                referred_to_opendata_request=models.Request.query.filter(referred_to_opendata_filter).all()
                referred_to_other_agency_request=models.Request.query.filter(referred_to_other_agency_filter).all()
                date_format='%Y-%m-%d'
            elif "fullYear" in public_filter:
                overdue_request=models.Request.query.filter(overdue_filter).all()
                notdue_request=models.Request.query.filter(notoverdue_filter).all()
                date_now = datetime.now()
                date_start_of_year = a = date(date.today().year, 1, 1)
                d_string = date_now.strftime(date_format)
                d_string_2 = date_start_of_year.strftime(date_format)
                min_date_received = str(datetime.strptime(d_string_2, date_format))
                max_date_received = str(datetime.strptime(d_string, date_format))
                min_date_received = min_date_received[0:-9]
                max_date_received = max_date_received[0:-9]
                received_request = received_request.filter(and_(models.Request.date_received >= min_date_received,
                                          models.Request.date_received <= max_date_received))
                published_request = published_request.filter(and_(models.Request.date_received >= min_date_received, models.Request.date_received <= max_date_received))
                denied_request=models.Request.query.filter(denied_filter).all()
                granted_and_closed_request=models.Request.query.filter(granted_and_closed_filter).all()
                granted_in_part_request=models.Request.query.filter(granted_in_part_filter).all()
                no_customer_response_request=models.Request.query.filter(no_customer_response_filter).all()
                out_of_jurisdiction_request=models.Request.query.filter(out_of_jurisdiction_filter).all()
                referred_to_nyc_gov_request=models.Request.query.filter(referred_to_nyc_gov_filter).all()
                referred_to_opendata_request=models.Request.query.filter(referred_to_opendata_filter).all()
                referred_to_other_agency_request=models.Request.query.filter(referred_to_other_agency_filter).all()
                referred_to_publications_portal_request=models.Request.query.filter(referred_to_publications_portal_filter).all()
            if calendar_filter == "rolling":
                date_format='%Y-%m-%d'
                overdue_request=models.Request.query.filter(overdue_filter).all()
                notdue_request=models.Request.query.filter(notoverdue_filter).all()
                date_now = datetime.now()
                d_string = date_now.strftime(date_format)
                min_date_received = str(datetime.strptime(d_string, date_format) - timedelta(365))
                max_date_received = str(datetime.strptime(d_string, date_format))
                min_date_received = min_date_received[0:-9]
                max_date_received = max_date_received[0:-9]
                received_request = received_request.filter(and_(models.Request.date_received >= min_date_received,
                                          models.Request.date_received <= max_date_received))
                published_request = published_request.filter(and_(models.Request.date_received >= min_date_received, models.Request.date_received <= max_date_received))
                denied_request=models.Request.query.filter(denied_filter).all()
                granted_and_closed_request=models.Request.query.filter(granted_and_closed_filter).all()
                granted_in_part_request=models.Request.query.filter(granted_in_part_filter).all()
                no_customer_response_request=models.Request.query.filter(no_customer_response_filter).all()
                out_of_jurisdiction_request=models.Request.query.filter(out_of_jurisdiction_filter).all()
                referred_to_nyc_gov_request=models.Request.query.filter(referred_to_nyc_gov_filter).all()
                referred_to_opendata_request=models.Request.query.filter(referred_to_opendata_filter).all()
                referred_to_other_agency_request=models.Request.query.filter(referred_to_other_agency_filter).all()
                referred_to_publications_portal_request=models.Request.query.filter(referred_to_publications_portal_filter).all()
            if staff_filter != "all":
                staff_id = int(staff_filter)
                overdue_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(overdue_filter).filter(models.Owner.is_point_person == True).all()
                notdue_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(notoverdue_filter).filter(models.Owner.is_point_person == True).all()
                received_request=received_request.filter(models.Request.id == models.Owner.request_id).filter(models.Owner.user_id == staff_id).filter(models.Owner.is_point_person == True)
                published_request=published_request.filter(models.Request.id == models.Owner.request_id).filter(published_filter).filter(models.Owner.user_id == staff_id).filter(models.Owner.is_point_person == True)
                denied_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(denied_filter).filter(models.Owner.user_id == staff_id).all()
                granted_and_closed_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(granted_and_closed_filter).filter(models.Owner.user_id == staff_id).all()
                granted_in_part_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(granted_in_part_filter).filter(models.Owner.user_id == staff_id).all()
                no_customer_response_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(no_customer_response_filter).filter(models.Owner.user_id == staff_id).all()
                out_of_jurisdiction_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(out_of_jurisdiction_filter).filter(models.Owner.user_id == staff_id).all()
                referred_to_nyc_gov_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(referred_to_nyc_gov_filter).filter(models.Owner.user_id == staff_id).all()
                referred_to_opendata_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(referred_to_opendata_filter).filter(models.Owner.user_id == staff_id).all()
                referred_to_other_agency_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(referred_to_other_agency_filter).filter(models.Owner.user_id == staff_id).all()
                referred_to_publications_portal_request=models.Request.query.filter(models.Request.id == models.Owner.request_id).filter(referred_to_publications_portal_filter).filter(models.Owner.user_id == staff_id).all()

            response={
                "status" : "ok",
                "data" : [
                    {"label" : "Received", "value" : len(received_request.all()), "callback" : "received"},
                    {"label" : "Published", "value" : len(published_request.all()), "callback" : "received"},
                    {"label" : "Denied", "value" : len(denied_request), "callback" : "denied"},
                    {"label" : "Granted And Closed", "value" : len(granted_and_closed_request), "callback" : "granted_and_closed"},
                    {"label" : "Granted In Part", "value" : len(granted_in_part_request), "callback" : "granted_in_part"},
                    {"label" : "No Customer Response", "value" : len(no_customer_response_request), "callback" : "no_customer_response"},
                    {"label" : "Out of Jurisdiction", "value" : len(out_of_jurisdiction_request), "callback" : "out_of_jurisdiction"},
                    {"label" : "Referred to NYC.gov", "value" : len(referred_to_nyc_gov_request), "callback" : "referred_to_nyc_gov_request"},
                    {"label" : "Referred to Open Data", "value" : len(referred_to_opendata_request), "callback" : "referred_to_opendata_request"},
                    {"label" : "Referred to Other Agency", "value" : len(referred_to_other_agency_request), "callback" : "referred_to_other_agency_request"},
                    {"label" : "Referred to Publications Portal", "value" : len(referred_to_publications_portal_request), "callback" : "referred_to_publications_portal_request"}
                ]
            }
        except Exception, e:
            response={
                "status" : "failed",
                "data" : "fail to find overdue request",
                 "exception": e
            }
        return jsonify(response)
    if report_type == "received":
        try:
            received_request=models.Request.query.all()
            response = {
                "status" : "ok",
                "data" : [
                    {"label" : "Received", "value" : len(received_request), "callback" : "received"}
                ]
            }

        except Exception, e:
            response = {
                "status": "failed",
                "data": "fail to find overdue request"
            }
        return jsonify(response)
    else:
        response = {
            "status": "failed",
            "data": "unregonized request"
        }
        return jsonify(response)


@app.route("/report")
def report():
    users=models.User.query.all()
    users=models.User.query.order_by(models.User.alias.asc()).all()
    departments_all = models.Department.query.all()
    agency_data = []
    for d in departments_all:
        agency_data.append({'name': d.name, 'id': d.id})

    overdue_request=models.Request.query.filter(models.Request.overdue == True).all()
    app.logger.info("\n\nOverdue Requests %s" %(len(overdue_request)))
    return render_template('report.html', users=users, agency_data=agency_data)

@app.route("/submit", methods=["POST"])
def submit():
    if recaptcha.verify():
        pass
    else:
        pass

@app.route("/changeprivacy", methods=["POST","GET"])
def change_privacy():
    req=get_obj("Request",request.form['request_id'])
    privacy=request.form['privacy setting']
    field=request.form['fieldtype']
    #field will either be title or description
    print request.form
    print "THE REQUEST PRIVACY SETTING IS BEING SET TO: " + str(privacy)
    app.logger.info("Changing privacy function")
    prr.change_privacy_setting(request_id=request.form['request_id'],privacy=privacy,field=field)
    return redirect(url_for('show_request_for_city',request_id=request.form['request_id']))

@app.route("/<page>")
def any_page(page):
    try:
        return render_template('%s.html' % (page))
    except:
        return page_not_found(404)

@app.errorhandler(400)
def bad_request(e):
    return render_template("400.html"), 400
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404
@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500
@app.errorhandler(403)
def access_denied(e):
    return redirect(url_for('login'))
@app.errorhandler(501)
def unexplained_error(e):
    return render_template("501.html"), 501
