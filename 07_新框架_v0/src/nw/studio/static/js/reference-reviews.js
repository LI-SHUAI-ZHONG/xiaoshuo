import {enc} from './api.js';

export function referenceReviews(queue) {
  return [
    ...queue.classifications.map(book=>({text:`《${book.title}》等待分类审核`, url:`staging/${enc(book.id)}`})),
    ...queue.structures.map(book=>({text:`核对《${book.title}》的拆解稿 · 修订 ${book.version}`, url:`staging/${enc(book.id)}`})),
    ...queue.methods.map(method=>({text:`核对制作方法《${method.title}》 · 修订 ${method.version}`, url:`kb/items?method=${enc(method.id)}`})),
  ];
}
