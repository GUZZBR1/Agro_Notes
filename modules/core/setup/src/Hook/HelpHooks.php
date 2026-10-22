<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Routing\RouteMatchInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_setup\SetupFormPluginManager;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

/**
 * Help hook implementations for farm_setup.
 */
class HelpHooks {

  use StringTranslationTrait;

  public function __construct(
    #[Autowire(service: 'plugin.manager.setup_form')]
    protected SetupFormPluginManager $setupFormPluginManager,
  ) {}

  /**
   * Implements hook_help().
   */
  #[Hook('help')]
  public function help($route_name, RouteMatchInterface $route_match) {
    $output = '';

    // Setup wizard forms.
    if (str_starts_with($route_name, 'farm.setup.wizard')) {
      $plugin_id = $route_match->getParameter('plugin_id');
      $plugin = $this->setupFormPluginManager->createInstance($plugin_id);
      $output = $plugin->getDescription();
    }

    // Modules form.
    if ($route_name == 'farm_setup.modules') {
      $output .= '<p>' . $this->t('Select the core and community farmOS modules that you would like to be installed.') . '</p>';
    }

    return $output;
  }

}
