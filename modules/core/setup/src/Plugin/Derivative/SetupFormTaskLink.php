<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Plugin\Derivative;

use Drupal\Component\Plugin\Derivative\DeriverBase;
use Drupal\Core\Plugin\Discovery\ContainerDeriverInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_setup\SetupFormPluginManager;
use Symfony\Component\DependencyInjection\Attribute\Autowire;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Provides task links for setup forms.
 */
class SetupFormTaskLink extends DeriverBase implements ContainerDeriverInterface {

  use StringTranslationTrait;

  public function __construct(
    #[Autowire(service: 'plugin.manager.setup_form')]
    protected SetupFormPluginManager $setupFormPluginManager,
  ) {}

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, $base_plugin_id) {
    return new static(
      $container->get('plugin.manager.setup_form'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function getDerivativeDefinitions($base_plugin_definition) {
    $links = [];

    // Add a link for each setup form plugin.
    // The first one will be farm.setup.wizard.
    $plugins = $this->setupFormPluginManager->getDefinitions();
    foreach ($plugins as $id => $plugin) {
      $route_name = 'farm.setup.wizard';
      $base_route = 'farm.setup.wizard';
      if ($id != array_key_first($plugins)) {
        $route_name .= '.' . $id;
      }
      $links[$route_name] = [
        'title' => $plugin['task_title'],
        'route_name' => $route_name,
        'base_route' => $base_route,
        'weight' => $plugin['weight'],
      ] + $base_plugin_definition;
    }

    return $links;
  }

}
