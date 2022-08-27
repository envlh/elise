import elise
import utils


def label(features, features_rev):
    r = []
    for feature in features:
        r.append(features_rev[feature])
    return ' '.join(r)


def pronoun(features):
    if 'Q110786' in features:
        if 'Q21714344' in features:
            return 'je'
        elif 'Q51929049' in features:
            return 'tu'
        elif 'Q51929074' in features:
            return 'iel'
    elif 'Q146786' in features:
        if 'Q21714344' in features:
            return 'nous'
        elif 'Q51929049' in features:
            return 'vous'
        elif 'Q51929074' in features:
            return 'iels'


def main():
    features = utils.load_json_file('conf/fr_features.json')
    features_rev = dict((v, k) for k, v in features.items())
    patterns = utils.load_json_file('conf/fr_group_1.json')
    lemma = 'chanter'
    group = 'Q2993354'
    forms = elise.generate_forms(features, patterns, lemma, group)
    i = 1
    for form in forms:
        print('; Form {}<nowiki>:</nowiki>'.format(i))
        print(':; A label.')
        print(':: <q>{}</q>'.format(label(form['grammaticalFeatures'], features_rev)))
        print(':; An example sentence.')
        print(':: <code>{} [{}]</code>'.format(pronoun(form['grammaticalFeatures']), form['representations']['fr']['value']))
        print(':; A list of grammatical feature item IDs.')
        print(':: {{{{Q|{}}}}}'.format('}}, {{Q|'.join(form['grammaticalFeatures'])))
        i += 1


if __name__ == '__main__':
    main()
