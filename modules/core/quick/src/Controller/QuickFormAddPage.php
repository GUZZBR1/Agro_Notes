<?php

declare(strict_types=1);

namespace Drupal\farm_quick\Controller;

use Drupal\Component\Utility\Html;
use Drupal\Core\Controller\ControllerBase;
use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Link;
use Drupal\farm_quick\Plugin\QuickForm\ConfigurableQuickFormInterface;
use Drupal\farm_quick\QuickFormPluginManager;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

/**
 * Page that renders links to create instances of quick form plugins.
 */
class QuickFormAddPage extends ControllerBase {

  use AutowireTrait;

  public function __construct(
    #[Autowire(service: 'plugin.manager.quick_form')]
    protected QuickFormPluginManager $quickFormPluginManager,
  ) {}

  /**
   * Add quick form page callback.
   *
   * @return array
   *   Render array.
   */
  public function addPage(): array {

    $render = [
      '#theme' => 'entity_add_list',
      '#bundles' => [],
      '#cache' => [
        'tags' => $this->quickFormPluginManager->getCacheTags(),
      ],
    ];

    // Filter to configurable quick form plugins.
    $plugins = array_filter($this->quickFormPluginManager->getDefinitions(), function (array $plugin) {
      if ($this->quickFormPluginManager->createInstance($plugin['id']) instanceof ConfigurableQuickFormInterface) {
        return TRUE;
      }
      return FALSE;
    });

    if (empty($plugins)) {
      $render['#add_bundle_message'] = $this->t('No quick forms are available. Enable a module that provides quick forms.');
    }

    // Add link for each configurable plugin.
    foreach ($plugins as $plugin_id => $plugin) {
      $render['#bundles'][$plugin_id] = [
        'label' => Html::escape($plugin['label']->render() ?? ''),
        'description' => Html::escape($plugin['description']->render() ?? ''),
        'add_link' => Link::createFromRoute($plugin['label'], 'farm_quick.add_form', ['plugin' => $plugin_id]),
      ];
    }

    return $render;
  }

}
