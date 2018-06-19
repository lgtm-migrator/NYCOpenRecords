from itertools import groupby
from operator import itemgetter
from sqlalchemy import or_
from typing import Sequence

from app.models import Agencies, LetterTemplates, Reasons


def get_active_users_as_choices(agency_ein):
    """
    Retrieve a list of users that are active for a given agency
    :param agency_ein: Agency EIN (String)
    :return: A list of user tuples (id, name)
    """
    active_users = sorted(
        [
            (user.get_id(), user.name)
            for user in Agencies.query.filter_by(ein=agency_ein).one().active_users
        ],
        key=lambda x: x[1],
    )
    active_users.insert(0, ("", "All"))
    return active_users


def get_reasons(agency_ein, reason_type=None):
    """Retrieve the determination reasons (used in emails) for the specified agency as a JSON object. If reason_type is
    provided, only retrieve determination_reasons of that type.

    Args:
        agency_ein (str): Agency EIN
        reason_type (str): One of ("denial", "closing", "re-opening")

    Returns:
        dict:
            {
                'type_', [(reason_id, reason_title),...]
            }
    """
    if reason_type is not None:
        reasons = (
            Reasons.query.with_entities(Reasons.id, Reasons.title, Reasons.type)
            .filter(
                Reasons.type == reason_type,
                or_(Reasons.agency_ein == agency_ein, Reasons.agency_ein == None),
            )
            .all()
        )
    else:
        reasons = (
            Reasons.query.with_entities(Reasons.id, Reasons.title, Reasons.type)
            .filter(or_(Reasons.agency_ein == agency_ein, Reasons.agency_ein == None))
            .all()
        )
    grouped_reasons = list(_group_items(reasons, 2))

    reasons_dict = {}

    for group in grouped_reasons:
        determination_type = group[0]
        reasons = group[1]

        reasons_dict[determination_type] = []

        for reason in reasons:
            reasons_dict[determination_type].append((reason[0], reason[1]))

    return reasons_dict


def get_letter_templates(agency_ein, template_type=None):
    """
    Retrieve letter templates for the specified agency as a JSON object. If template type is provided, only get
    templates of that type.

    :param agency_ein: Agency EIN (String)
    :param template_type: One of "acknowledgment", "denial", "closing", "letter", "extension", "re-opening" (String)
    :return: Dictionary

        {
            'type_': [(template_id, template_name),...]
        }
    """
    if template_type is not None:
        templates = (
            LetterTemplates.query.with_entities(
                LetterTemplates.id, LetterTemplates.title, LetterTemplates.type_
            )
            .filter(LetterTemplates.type_ == template_type)
            .all()
        )
    else:
        templates = (
            LetterTemplates.query.with_entities(
                LetterTemplates.id, LetterTemplates.title, LetterTemplates.type_
            )
            .filter_by(agency_ein=agency_ein)
            .all()
        )

    grouped_templates = list(_group_items(templates, 2))

    template_dict = {}

    for group in grouped_templates:
        template_type = group[0]
        templates = group[1]

        template_dict[template_type] = []

        for template in templates:
            template_dict[template_type].append((template[0], template[1]))

    return template_dict


def _group_items(items: Sequence[Sequence], sort_index: int) -> tuple:
    """Group a collection of items by a specified key
    
    Args:
        collections (Sequence): A collection of items to be grouped
        sort_index (int): Index of the item to use for grouping
    
    Yields:
        tuple:
            (
                items[sort_index_1], (Sequence[i], Sequence[j], ...),
                items[sort_index_2], (Sequence[i], Sequence[j], ...),
                ...
            )        
    """
    grouped = groupby(items, itemgetter(sort_index))

    for item_index, sub_iter in grouped:
        yield item_index, list(sub_iter)
