module.exports = function (api) {
  const isTest = api.env('test');
  api.cache(true);
  return {
    presets: [['babel-preset-expo', { jsxImportSource: 'nativewind' }], 'nativewind/babel'],
    plugins: [
      ...(isTest ? ['babel-plugin-transform-import-meta'] : []),
      'react-native-worklets/plugin',
    ],
  };
};
