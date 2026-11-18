# Fotografias reais usadas na demonstração do DoaFácil

As fotografias abaixo representam **anúncios fictícios para demonstração acadêmica**. Não são fotografias dos objetos de doadores reais. As fotos enviadas pelos usuários continuam sendo exibidas normalmente.

| Área | Fotógrafo | Fotografia original |
|---|---|---|
| Mochila escolar | Matt Ragland | [Ver no Unsplash](https://unsplash.com/photos/flat-lay-photography-of-blue-backpack-beside-book-and-silver-macbook-02z1I7gv4ao) |
| Livros | Fiona Murray-deGraaff | [Ver no Unsplash](https://unsplash.com/photos/a-stack-of-books-sitting-on-top-of-each-other-cQIcyN0Hn3o) |
| Ursinho de pelúcia | Milan Cobanov | [Ver no Unsplash](https://unsplash.com/photos/a-small-teddy-bear-sits-on-a-windowsill-_Mpj-shrKGM) |
| Luminária | Vladislav Glukhotko | [Ver no Unsplash](https://unsplash.com/photos/a-lamp-that-is-on-top-of-a-table-SbGLQAtv8Gk) |
| Casaco | Brock Solis | [Ver no Unsplash](https://unsplash.com/photos/man-wearing-grey-hoodie-zJCeldxQS0c) |
| Cadernos | Marissa Grootes | [Ver no Unsplash](https://unsplash.com/photos/three-assorted-color-notebooks-17ItlICPSzs) |
| Eletrônicos | Sven Kucinic | [Ver no Unsplash](https://unsplash.com/photos/person-using-smartphone-ktSdj3aV0IA) |
| Foto principal / login | Joel Muniz | [Ver no Unsplash](https://unsplash.com/photos/people-standing-in-front-of-brown-cardboard-boxes-y3ZY6qFln_g) |

Imagens publicadas pelos autores sob a [Licença Unsplash](https://unsplash.com/license). As imagens ilustrativas são carregadas por URLs do domínio `images.unsplash.com`, portanto necessitam de conexão com a internet. Não copie nem revenda as imagens isoladamente. Antes de publicar o sistema para o público, revise as imagens e as condições de licenciamento vigentes.

**Como funciona:** o `app.py` contém um dicionário `DEMO_PHOTOS` com os endereços das fotografias. Um filtro Jinja chamado `photo_url` converte automaticamente as referências SVG de demonstração que já estão no SQLite para as fotos reais, sem precisar apagar ou recriar o banco. Imagens enviadas pelos usuários não são alteradas.
