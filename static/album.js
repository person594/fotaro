function add_img_to_flow(hash) {
    flow = document.getElementById('album-flow');
    img = document.createElement('img');
    img.src = "/photo/" + hash;
    flow.append(img);
}

add_img_to_flow("362607ab46eb80b2c7961ce76bdc7b440910d59b5e8840ea45512dfd16113a87");
add_img_to_flow("13c3096dc1a50d2061ee96110aa8abaf23266f43deab7e78d6aec71dcc6563f6");
