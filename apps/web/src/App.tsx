import { Route, Switch } from 'wouter';
import { CatalogProvider } from '@/components/CatalogProvider';
import { Layout } from '@/components/layout/Layout';
import Autores from '@/pages/Autores';
import Comprar from '@/pages/Comprar';
import Contato from '@/pages/Contato';
import Home from '@/pages/Home';
import Loja from '@/pages/Loja';
import NotFound from '@/pages/NotFound';
import Privacidade from '@/pages/Privacidade';
import Produto from '@/pages/Produto';
import Sobre from '@/pages/Sobre';
import Termos from '@/pages/Termos';

export default function App() {
  return (
    <CatalogProvider>
      <Layout>
        <Switch>
          <Route path="/" component={Home} />
          <Route path="/loja" component={Loja} />
          <Route path="/produto/:id" component={Produto} />
          <Route path="/comprar/:id" component={Comprar} />
          <Route path="/comprar" component={Comprar} />
          <Route path="/sobre" component={Sobre} />
          <Route path="/contato" component={Contato} />
          <Route path="/autores" component={Autores} />
          <Route path="/termos" component={Termos} />
          <Route path="/privacidade" component={Privacidade} />
          <Route component={NotFound} />
        </Switch>
      </Layout>
    </CatalogProvider>
  );
}
