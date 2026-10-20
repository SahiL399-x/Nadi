import { render } from '@testing-library/react-native';
import { DoctorsMap } from '@/components/DoctorsMap';

// MapLibre is a native module — it cannot render under jest (no native dev build
// here). Mock it with a plain host-tag stub so the pure React tree (one Marker per
// doctor) is still assertable. The stub intentionally avoids both
// `React.createElement` and any component imported from `react-native` (e.g.
// `View`): either one gets rewritten by the nativewind/css-interop babel plugin
// to reference an injected `_ReactNativeCSSInterop` module import, and that
// injected reference trips Jest's "out-of-scope variable" guard on `jest.mock()`
// factories. A JSX element whose tag is an arbitrary string (via a capitalized
// variable holding a string, so JSX treats it as a component reference rather
// than a literal intrinsic tag) sidesteps both: it compiles through the
// automatic jsx-runtime (not `React.createElement`) and isn't recognized as a
// react-native import, so nativewind leaves it untouched.
jest.mock('@maplibre/maplibre-react-native', () => {
  const StubTag: any = 'nadi-maplibre-stub';
  const Stub = ({ children, ...p }: any) => <StubTag {...p}>{children}</StubTag>;
  return { __esModule: true, Map: Stub, Camera: Stub, Marker: Stub };
});

test('renders a marker per doctor', async () => {
  const docs = [
    { id: 'd1', name: 'A', lat: 19.99, lng: 73.79, feeInr: 300 },
    { id: 'd2', name: 'B', lat: 20.0, lng: 73.8, feeInr: 500 },
  ] as any;
  const { root, getByTestId } = await render(<DoctorsMap doctors={docs} />);
  expect(root).toBeTruthy();
  // one marker per doctor: the stub forwards `testID` onto the rendered host element
  expect(getByTestId('doctor-marker-d1')).toBeTruthy();
  expect(getByTestId('doctor-marker-d2')).toBeTruthy();
});
