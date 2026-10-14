"""Source heading retrieval; no benchmark IDs, generated rules or legal decisions."""
import math
import re
from collections import Counter

from .security import normalize

STOP = set('toi cua co la va hay thi ma khi duoc theo nhung nao the nhu voi trong tai ve cho den tren mot cac nhieu nay do khong chua luon can con phai het toan bo ngay nam ha noi xin hoi giup hay lieu se da dang'.split())


def terms(text):
    text = normalize(text)
    for citizen, statutory in [('so do', 'giay chung nhan'), ('so hong', 'giay chung nhan'),
                               ('den bu', 'boi thuong')]:
        text = text.replace(citizen, statutory)
    return [w for w in re.findall(r'[a-z0-9]+', text) if len(w) > 1 and w not in STOP]


class HeadingIndex:
    """Bounded article heading index, inherited by continuation paragraphs.

    Only short source prefixes are retained. It adds candidates to RRF without
    changing the corpus or deciding whether an article legally applies.
    """
    def __init__(self, rows):
        headings = {}
        for row in rows:
            match = re.search(r'Điều\s+\d+[a-z]?\s*[.:]\s*([^\n]+)', row['prefix'], re.I)
            if match:
                title = re.split(r'\s+1\.\s|\s+[a-zđ]\)\s', match[1], maxsplit=1)[0][:260]
                headings.setdefault((row['document_id'], row['locator'].split(' · ')[0]), title)
        self.entries = []
        self.df = Counter()
        for row in rows:
            title = headings.get((row['document_id'], row['locator'].split(' · ')[0]), '')
            tokens = terms(title)
            if not tokens:
                continue
            entry = {k: row[k] for k in ('id', 'document_id', 'locator')}
            entry.update(title=title, counts=Counter(tokens), body=set(terms(row['prefix'])), length=len(tokens))
            self.entries.append(entry)
            self.df.update(set(tokens))
        self.average = sum(e['length'] for e in self.entries) / max(1, len(self.entries))

    def rank(self, query, eligible_docs, exact_docs=(), limit=20):
        query_terms = set(terms(query))
        size = len(self.entries)
        scores = []
        for e in self.entries:
            if e['document_id'] not in eligible_docs:
                continue
            score = 0.0
            for term in query_terms:
                count = e['counts'].get(term, 0)
                if count:
                    idf = math.log(1 + (size - self.df[term] + .5)/(self.df[term] + .5))
                    score += idf * count * 2.2 / (count + 1.2 * (.25 + .75 * e['length']/max(1, self.average)))
            if score:
                heading=normalize(e['title'])
                topics=[t for t in ('boi thuong','ho tro','tai dinh cu','quy hoach','khieu nai') if t in normalize(query)]
                if topics and not any(t in heading for t in topics):
                    score *= .25
                score += .15 * len(query_terms & e['body'])
                if e['document_id'] in exact_docs:
                    score *= 2
                scores.append((score, e['id']))
        ranked=sorted(scores, key=lambda item: (-item[0], item[1]))
        groups=Counter()
        entries={e['id']:e for e in self.entries}
        selected=[]
        for item in ranked:
            entry=entries[item[1]];key=(entry['document_id'],entry['locator'])
            if groups[key]>=2:continue
            groups[key]+=1;selected.append(item)
            if len(selected)>=limit:break
        return selected

    def articles(self, query, eligible_docs, limit=40):
        entries={e['id']:e for e in self.entries}
        found={}
        for score,chunk_id in self.rank(query,eligible_docs,limit=len(self.entries)):
            e=entries[chunk_id];key=(e['document_id'],e['locator'])
            found.setdefault(key,{'document_id':key[0],'locator':key[1],'heading':e['title']})
            if len(found)>=limit:break
        return list(found.values())
