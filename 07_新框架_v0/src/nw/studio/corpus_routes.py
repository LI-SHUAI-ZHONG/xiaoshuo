"""Routes for versioned source structures, durable jobs and derived methods."""
from typing import Any

from nw.studio.corpus_methods import manual_method


def get(library: Any,segs: list[str],query: dict) -> dict | None:
    if segs==['corpus','catalog']:return library.corpus_catalog()
    if len(segs)<3 or segs[0]!='staging' or segs[2]!='corpus':return None
    book=segs[1]
    if len(segs)==3:
        version=query.get('version',[''])[0]
        return library.get_corpus(book,int(version) if version else None)
    if segs[3:]==['jobs']:return library.list_corpus_jobs(book)
    if len(segs)==5 and segs[3]=='jobs':return library.get_corpus_job(book,segs[4])
    if len(segs)==7 and segs[3]=='jobs' and segs[5]=='calls':return library.corpus_call_record(book,segs[4],int(segs[6]))
    return None


def post(library: Any,segs: list[str],body: dict) -> dict | None:
    if len(segs)<4 or segs[0]!='staging' or segs[2]!='corpus':return None
    book=segs[1]
    actions={'initialize':library.initialize_corpus,'save':library.save_corpus,'record':library.edit_corpus_record,
             'review':library.review_corpus,'estimate':library.estimate_corpus,'jobs':library.start_corpus_job}
    if len(segs)==4:
        if segs[3]=='methods':return manual_method(library,book,body)
        if segs[3] in actions:return actions[segs[3]](book,body)
    if len(segs)==5 and segs[3]=='jobs':return library.control_corpus_job(book,segs[4],body)
    return None
