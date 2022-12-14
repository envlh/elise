import copy
import json
import logging

import utils


def is_valid_lexeme(lexeme):
    if lexeme['language'] != 'Q150':
        return False
    if lexeme['lexicalCategory'] != 'Q24905':
        return False
    if 'fr' not in lexeme['lemmas']:
        return False
    return True


def get_group(lexeme):
    if 'P5186' not in lexeme['claims']:
        return None
    if len(lexeme['claims']['P5186']) != 1:
        return None
    group = lexeme['claims']['P5186'][0]['mainsnak']['datavalue']['value']['id']
    if group not in ('Q2993354', 'Q2993353', 'Q2993358'):
        return None
    return group


def is_handled_lexeme(lexeme, group):
    lemma = lexeme['lemmas']['fr']['value']
    # pronominal verb
    if lemma[:3] == 'se ' or lemma[:2] == 's\'' or lemma[:2] == 's’':
        return False
    # multiples conjugaisons (exemple : copier-coller)
    if '-' in lexeme['lemmas']['fr']['value']:
        return False
    # premier groupe
    if group == 'Q2993354':
        if lemma[-2:] != 'er':
            return False
        # exceptions https://fr.wikipedia.org/wiki/Conjugaison_des_verbes_du_premier_groupe
        if lemma[-4:-3] == 'e':
            return False
        if lemma[-4:-3] == 'é':
            return False
        # orthographe 1990 https://dictionnaire.lerobert.com/guide/rectifications-de-l-orthographe-de-1990-regles
        if lemma[-4:] == 'eler' or lemma[-4:] == 'eter':
            return False
        return True
    # deuxième groupe
    elif group == 'Q2993353':
        if lemma[-2:] != 'ir':
            return False
        # exceptions
        if lemma == 'haïr' or lemma.endswith('fleurir'):
            return False
        return True
    return False


def clean_grammatical_features(forms, replacements):
    forms_copy = copy.deepcopy(forms)
    for form in forms_copy:
        features = []
        for feature in form['grammaticalFeatures']:
            if feature in replacements:
                features.extend(replacements[feature])
            else:
                features.append(feature)
        form['grammaticalFeatures'] = features
    return forms_copy


def generate_forms(features, patterns, lemma, group):
    forms = []
    root = lemma[:-2]
    for pattern in patterns:
        representations = []
        suffix = pattern['suffix']
        # envoyer, renvoyer
        if group == 'Q2993354' and lemma in ('envoyer', 'renvoyer') and (('indicatif' in pattern['features'] and 'futur simple' in pattern['features']) or ('conditionnel' in pattern['features'] and 'présent' in pattern['features'])):
            representations.append('{}err{}'.format(root[:-2], suffix[2:]))
        # -cer
        elif group == 'Q2993354' and root[-1] == 'c' and suffix[0] in ('a', 'â', 'o'):
            representations.append('{}ç{}'.format(root[:-1], suffix))
        # -ger
        elif group == 'Q2993354' and root[-1] == 'g' and suffix[0] in ('a', 'â', 'o'):
            representations.append('{}e{}'.format(root, suffix))
        # -ayer
        elif group == 'Q2993354' and root[-2:] == 'ay' and (suffix in ('e', 'es', 'ent') or (suffix[:2] == 'er' and suffix != 'er')):
            representations.append('{}{}'.format(root, suffix))
            representations.append('{}i{}'.format(root[:-1], suffix))
        # -oyer -uyer
        elif group == 'Q2993354' and (root[-2:] == 'oy' or root[-2:] == 'uy') and (suffix in ('e', 'es', 'ent') or (suffix[:2] == 'er' and suffix != 'er')):
            representations.append('{}i{}'.format(root[:-1], suffix))
        # default
        else:
            representations.append('{}{}'.format(root, suffix))
        grammatical_features = []
        for feature in pattern['features']:
            grammatical_features.append(features[feature])
        for representation in representations:
            form = {'representations': {'fr': {'language': 'fr', 'value': representation}}, 'grammaticalFeatures': grammatical_features, 'claims': {}, 'add': ''}
            forms.append(form)
    return forms


def are_forms_equal(a, b):
    if a['representations']['fr']['value'] != b['representations']['fr']['value']:
        return False
    if set(a['grammaticalFeatures']) != set(b['grammaticalFeatures']):
        return False
    return True


def compute_forms(base_forms, generated_forms):
    error = 0
    computed_forms = []
    # existing forms
    for form_e in base_forms:
        computed_forms.append(form_e)
        found = False
        for form_g in generated_forms:
            if are_forms_equal(form_e, form_g):
                found = True
                break
        if not found:
            error += 1
            logging.error('This existing form has no match: {}'.format(form_e))
    # generated forms
    for form_g in generated_forms:
        found = False
        for form_e in base_forms:
            if are_forms_equal(form_e, form_g):
                found = True
                break
        if not found:
            computed_forms.append(form_g)
    return error, computed_forms


def edit_lexeme(site, lid, lexeme):
    request = {
        'action': 'wbeditentity',
        'format': 'json',
        'summary': '[[Wikidata:Requests for permissions/Bot/EnvlhBot 4|Forms of French verbs]]',
        'token': site.tokens['edit'],
        'bot': '1',
        'id': lid,
        'baserevid': lexeme['lastrevid'],
        'data': json.dumps(lexeme, ensure_ascii=False),
    }
    site.simple_request(**request).submit()


def improve_lexeme(lid, features, replacements, site):
    lexeme = utils.fetch_url_json('https://www.wikidata.org/wiki/Special:EntityData/{}.json'.format(lid))['entities'][lid]
    if not is_valid_lexeme(lexeme):
        logging.error('{} is not a valid lexeme.'.format(lid))
        return
    group = get_group(lexeme)
    if group is None:
        logging.error('Lexeme {} does not have a valid group.'.format(lid))
        return
    if not is_handled_lexeme(lexeme, group):
        logging.error('Elise cannot handle lexeme {} at the moment.'.format(lid))
        return
    if group == 'Q2993354':
        patterns = utils.load_json_file('conf/fr_group_1.json')
    elif group == 'Q2993353':
        patterns = utils.load_json_file('conf/fr_group_2.json')
    else:
        logging.error('No pattern file for group {} used on lexeme {}.'.format(group, lid))
        return
    # clean existing forms
    clean_forms = clean_grammatical_features(lexeme['forms'], replacements)
    # print(json.dumps(clean_forms, ensure_ascii=False))
    # generate all forms
    generated_forms = generate_forms(features, patterns, lexeme['lemmas']['fr']['value'], group)
    # print(json.dumps(generated_forms, ensure_ascii=False))
    # merge forms
    error, computed_forms = compute_forms(clean_forms, generated_forms)
    # print(json.dumps(computed_forms, ensure_ascii=False))
    if error != 0:
        logging.error('Unrecognized forms in lexeme {}, no change applied. Link: https://www.wikidata.org/wiki/Lexeme:{}'.format(lid, lid))
    elif computed_forms == lexeme['forms']:
        logging.debug('No change needed to lexeme {}.'.format(lid))
    else:
        logging.info('Updating lexeme {}...'.format(lid))
        lexeme['forms'] = computed_forms
        edit_lexeme(site, lid, lexeme)
        logging.info('Done.')


def main():
    logging.getLogger().setLevel(logging.INFO)
    features = utils.load_json_file('conf/fr_features.json')
    replacements = utils.load_json_file('conf/fr_replacements.json')
    site = utils.get_site()
    lexemes = utils.sparql_query('SELECT DISTINCT ?lexeme { ?lexeme dct:language wd:Q150 ; wikibase:lexicalCategory wd:Q24905 ; wdt:P5186 ?group . OPTIONAL { ?lexeme ontolex:lexicalForm ?form } . VALUES ?group { wd:Q2993354 wd:Q2993353 } } GROUP BY ?lexeme HAVING (COUNT(DISTINCT ?form) < 51)')
    logging.info('{} verbs found.'.format(len(lexemes)))
    for lexeme in lexemes:
        lexeme_id = lexeme['lexeme']['value'][31:]
        improve_lexeme(lexeme_id, features, replacements, site)


if __name__ == '__main__':
    main()
